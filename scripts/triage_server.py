from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

# Import our new core logic
from executor.tools.email import EmailClient
from orchestrator.email_triage import EmailTriageOrchestrator
from executor.tools.transformation import OpenAIClient
from executor.tools.messaging import MessagingClient

load_dotenv()

app = FastAPI()

# Mount the static files from /web
app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/")
def read_root():
    from fastapi.responses import FileResponse
    return FileResponse("web/index.html")

@app.post("/api/test_connection")
async def test_connection_api(request: Request):
    data = await request.json()
    imap_server = data.get("imap_server")
    user = data.get("email_user")
    password = data.get("email_pass")
    
    if not all([imap_server, user, password]):
        return {"status": "error", "message": "Missing credentials"}

    try:
        import imaplib
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(user, password)
        mail.logout()
        return {"status": "success", "message": "Connection verified!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/triage")
async def run_triage_api(request: Request):
    data = await request.json()
    
    # Persistent Sync: Save this config for the background autopilot
    os.makedirs("data", exist_ok=True)
    with open("data/config.json", "w") as f:
        json.dump(data, f)
    
    rules = {
        "business_goal": data.get("goal"),
        "vips": data.get("vips"),
        "tone": data.get("tone"),
        "urgency_triggers": data.get("urgency")
    }
    
    ai = OpenAIClient()
    messaging = MessagingClient(
        webhook_url=data.get("msg_url"), 
        provider=data.get("msg_provider", "slack")
    )
    
    # Check if we should use real IMAP or Simulation
    use_simulation = not (data.get("email_user") and data.get("email_pass"))

    try:
        if use_simulation:
            # Create a 'Mock' orchestrator that uses the real AI judge but fake emails
            mock_emails = [
                {"subject": "Question about Invoice #402", "from": "vendor@supply.com", "body": "Can you check the status of this billing? We haven't received it."},
                {"subject": "Coffee next week?", "from": "friend@personal.com", "body": "Let me know if you have time for a chat."},
                {"subject": "Urgent: System Downtime", "from": "monitor@service.io", "body": "The main server is reporting errors."}
            ]
            
            # Use the orchestrator logic but swap the fetch step
            orchestrator = EmailTriageOrchestrator(None, ai, messaging_client=messaging)
            results = []
            for mail in mock_emails:
                decision = orchestrator._judge_email(mail, rules)
                # Still notify messaging in simulation if URL is provided
                if messaging.webhook_url:
                    messaging.send_triage_alert(mail, decision)
                results.append({"mail": mail, "triage": decision})
            
            return {"status": "simulation", "results": results}
        else:
            email = EmailClient(
                imap_server=data.get("imap_server"),
                smtp_server="smtp.gmail.com",
                email_user=data.get("email_user"),
                email_pass=data.get("email_pass")
            )
            orchestrator = EmailTriageOrchestrator(email, ai, messaging_client=messaging)
            results = orchestrator.run_triage(
                rules, 
                use_management=data.get("enable_filing", False)
            )
            return {"status": "success", "results": results}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

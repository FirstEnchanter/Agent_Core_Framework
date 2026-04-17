"""
Live Verification Script â€” Testing Real Credentials
Connects to Gmail and sends a real alert to Discord.
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from dotenv import load_dotenv
from executor.tools.email import EmailClient
from executor.tools.transformation import OpenAIClient
from executor.tools.messaging import MessagingClient
from executor.tools.history import TriageHistory
from orchestrator.email_triage import EmailTriageOrchestrator

async def run_test():
    load_dotenv()
    print("--- Agent Agent: Live Test Starting ---")
    
    # 1. Credentials
    GMAIL_USER = "1stenchanter.tv@gmail.com"
    GMAIL_PASS = "sbcamktwvzkiiwya"
    DISCORD_URL = "https://discord.com/api/webhooks/1493633054348935168/KuOnNmNNYUoW7O3p2XJGueSEfTh1OLkP1ziMDuX0fKnkYGNoSa5-oz40oVYZ0RDun10R"

    rules = {
        "business_goal": "Optimize for high-value strategic growth and client satisfaction.",
        "vips": "user@example.com",
        "tone": "Professional",
        "urgency_triggers": "Billing, downtime, media requests"
    }

    try:
        # 2. Setup Clients
        print("Connecting to Gmail IMAP...")
        email = EmailClient(
            imap_server="imap.gmail.com",
            smtp_server="smtp.gmail.com",
            email_user=GMAIL_USER,
            email_pass=GMAIL_PASS
        )

        print("Connecting to Discord Pipeline...")
        messaging = MessagingClient(
            webhook_url=DISCORD_URL,
            provider="discord"
        )

        history = TriageHistory()
        orchestrator = EmailTriageOrchestrator(email, OpenAIClient(), messaging, history)

        # 3. Execute
        print("Fetching latest emails and judging...")
        results = await orchestrator.run_triage(rules, use_management=False)
        
        print(f"DONE! Processed {len(results)} items.")
        for res in results:
            mail = res['mail']
            triage = res['triage']
            try:
                print(f" >> [{triage['category']}] {mail['subject']}")
            except:
                print(f" >> [{triage['category']}] [Subject Decoded]")

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_test())



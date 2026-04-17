import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment from root folder (three levels up from scripts)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_ROOT = os.path.dirname(ROOT_DIR)
load_dotenv(dotenv_path=os.path.join(WORKSPACE_ROOT, ".env"))

GUARDIAN_LOG = os.path.join(ROOT_DIR, "logs", "guardian_history.json")
WEBHOOK_URL = os.getenv("DISCORD_SECURITY_WEBHOOK_URL")

def _init_log():
    if not os.path.exists(os.path.dirname(GUARDIAN_LOG)):
        os.makedirs(os.path.dirname(GUARDIAN_LOG))
    if not os.path.exists(GUARDIAN_LOG):
        with open(GUARDIAN_LOG, 'w') as f:
            json.dump([], f)

def log_event(event_type, message, detail="", level="INFO"):
    _init_log()
    timestamp = datetime.now().isoformat()
    
    event = {
        "type": event_type,  # SECURITY, ERROR, BILLING, SYSTEM
        "timestamp": timestamp,
        "message": message,
        "detail": detail,
        "level": level       # INFO, WARNING, CRITICAL
    }
    
    try:
        with open(GUARDIAN_LOG, 'r+') as f:
            data = json.load(f)
            data.insert(0, event)
            f.seek(0)
            json.dump(data[:100], f, indent=4) # Keep last 100
            f.truncate()
    except Exception as e:
        print(f"FAILED TO SAVE GUARDIAN LOG: {e}")
    
    # Send Discord Notification if Webhook is set
    if WEBHOOK_URL:
        send_discord_alert(event)

def send_discord_alert(event):
    if not WEBHOOK_URL:
        return

    color = 0x3498db # blue (info)
    if event["level"] == "WARNING":
        color = 0xf1c40f # yellow
    elif event["level"] == "CRITICAL":
        color = 0xe74c3c # red

    payload = {
        "embeds": [{
            "title": f"🛡️ System Guardian — {event['type']}",
            "description": f"**{event['message']}**",
            "color": color,
            "fields": [
                {"name": "Level", "value": event["level"], "inline": True},
                {"name": "Timestamp", "value": event["timestamp"], "inline": True}
            ],
            "footer": {"text": "Automated Security Overseer"}
        }]
    }
    
    if event["detail"]:
        payload["embeds"][0]["fields"].append({
            "name": "Details", "value": f"```\n{event['detail'][:1000]}\n```"
        })

    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"FAILED TO SEND DISCORD ALERT: {e}")

def report_leak(leak_type, location):
    log_event(
        event_type="SECURITY",
        message=f"CRITICAL: Potential {leak_type} Detected",
        detail=f"Location: {location}\nAction: Commit/Push Blocked.",
        level="CRITICAL"
    )

def report_error(source, error_msg):
    log_event(
        event_type="ERROR",
        message=f"System Error in {source}",
        detail=error_msg,
        level="WARNING"
    )

"""
Background Agent Daemon  Layer 2: Orchestration
Runs 24/7 scanning for new emails based on saved rules.
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from executor.tools.email import EmailClient
from executor.tools.transformation import OpenAIClient
from executor.tools.messaging import MessagingClient
from executor.tools.history import TriageHistory
from orchestrator.email_triage import EmailTriageOrchestrator
from executor.tools.logging_tool import get_logger

log = get_logger(__name__)
load_dotenv()

CONFIG_PATH = "data/config.json"

async def run_autopilot():
    """Main daemon loop."""
    log.info("autopilot.daemon_started")
    
    # Persistent clients
    ai = OpenAIClient()
    history = TriageHistory()

    while True:
        if not os.path.exists(CONFIG_PATH):
            log.warning("autopilot.waiting_for_config")
            await asyncio.sleep(60)
            continue

        try:
            # 1. Load latest rules & credentials
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            rules = {
                "business_goal": config.get("goal"),
                "vips": config.get("vips"),
                "tone": config.get("tone"),
                "threshold": config.get("threshold", 4),
                "urgency_triggers": config.get("urgency")
            }

            # 2. Setup Clients
            email = EmailClient(
                imap_server=config.get("imap_server"),
                smtp_server="smtp.gmail.com",
                email_user=config.get("email_user"),
                email_pass=config.get("email_pass")
            )
            
            messaging = MessagingClient(
                webhook_url=config.get("msg_url"),
                provider=config.get("msg_provider", "slack")
            )

            orchestrator = EmailTriageOrchestrator(email, ai, messaging, history)
            
            # 3. Execute Triage
            log.info("autopilot.checking_inbox")
            # Run Triage Cycle
            results = await orchestrator.run_triage(
                rules, 
                use_management=config.get("enable_filing", False),
                folders=["INBOX", "[Gmail]/Spam"]
            )
            
            if results:
                log.info("autopilot.items_processed", count=len(results))
            else:
                log.info("autopilot.no_new_items")

        except Exception as e:
            log.error("autopilot.loop_error", error=str(e))

        # 4. Wait for next cycle (15 minutes)
        log.info("autopilot.sleeping", minutes=15)
        await asyncio.sleep(15 * 60)

if __name__ == "__main__":
    asyncio.run(run_autopilot())

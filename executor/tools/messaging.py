"""
Universal Messaging Tools — Layer 3: Execution
Dispatches triaged alerts to Slack, Discord, or Teams.
"""

import json
import requests
from typing import Dict, Any, Optional
from executor.tools.logging_tool import get_logger

log = get_logger(__name__)

class MessagingClient:
    """
    Universal Messaging Client supporting multi-platform webhooks.
    """
    def __init__(self, webhook_url: str = None, provider: str = "slack"):
        self.webhook_url = webhook_url
        self.provider = provider.lower()

    def send_triage_alert(self, mail: Dict[str, Any], triage: Dict[str, Any]):
        """
        Dispatches alert based on the selected provider's format.
        """
        if not self.webhook_url:
            return

        if self.provider == "slack":
            self._send_slack(mail, triage)
        elif self.provider == "discord":
            self._send_discord(mail, triage)
        elif self.provider == "teams":
            self._send_teams(mail, triage)
        else:
            self._send_generic(mail, triage)

    def _send_slack(self, mail: Dict[str, Any], triage: Dict[str, Any]):
        priority_emoji = "🔴 *URGENT*" if triage['priority'] >= 5 else "🟡 *PRIORITY*"
        payload = {
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"{priority_emoji} | *{triage['category']} Alert*"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*From:* {mail['from']}\n*Subject:* {mail['subject']}\n\n*Rationale:* {triage['rationale']}"}},
            ]
        }
        if triage.get('draft'):
            payload["blocks"].append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Suggested Response:*\n> {triage['draft']}"}})
        
        self._dispatch(payload)

    def _send_discord(self, mail: Dict[str, Any], triage: Dict[str, Any]):
        # Discord uses a slightly different embed format
        priority_color = 0xff0000 if triage['priority'] >= 5 else 0xffff00
        payload = {
            "embeds": [{
                "title": f"{triage['category']} Alert: {mail['subject']}",
                "description": f"**Rationale:** {triage['rationale']}\n\n**Draft:** {triage.get('draft', 'No draft provided.')}",
                "color": priority_color,
                "fields": [
                    {"name": "From", "value": mail['from'], "inline": True},
                    {"name": "Priority", "value": str(triage['priority']), "inline": True}
                ]
            }]
        }
        self._dispatch(payload)

    def send_agent_alert(self, agent_name: str, status: str, title: str, message: str, draft: Optional[str] = None):
        """
        Dispatches a generic agent status alert (e.g. for Bluesky Publisher)
        """
        if not self.webhook_url:
            return
            
        if self.provider == "discord":
            self._send_discord_agent(agent_name, status, title, message, draft)
        else:
            # Fallback for generic
            self._dispatch({"agent": agent_name, "status": status, "message": message, "draft": draft})

    def _send_discord_agent(self, agent_name: str, status: str, title: str, message: str, draft: Optional[str]):
        # SUCCESS = Green, FAILURE = Red, WARNING = Yellow
        color_map = {
            "SUCCESS": 0x00FF00,
            "FAILURE": 0xFF0000,
            "WARNING": 0xFFFF00
        }
        color = color_map.get(status.upper(), 0x145A5A)
        
        embed = {
            "title": f"[{status.upper()}] {agent_name}: {title}",
            "description": message,
            "color": color
        }
        
        if draft:
            # Add draft as a separate field so it formats nicely
            embed["fields"] = [
                {"name": "Content / Draft", "value": f"```\n{draft}\n```", "inline": False}
            ]
            
        payload = {"embeds": [embed]}
        self._dispatch(payload)

    def _send_teams(self, mail: Dict[str, Any], triage: Dict[str, Any]):
        # Microsoft Teams uses the Adaptive Cards / MessageCard format
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": f"Triage Alert: {triage['category']}",
            "themeColor": "0078D7",
            "title": f"{triage['category']} Alert",
            "sections": [{
                "facts": [
                    {"name": "From:", "value": mail['from']},
                    {"name": "Subject:", "value": mail['subject']},
                    {"name": "Rationale:", "value": triage['rationale']}
                ],
                "text": triage.get('draft', '')
            }]
        }
        self._dispatch(payload)

    def _send_generic(self, mail, triage):
        self._dispatch({"mail": mail, "triage": triage})

    def _dispatch(self, payload: Dict[str, Any]):
        try:
            requests.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            log.error("messaging.dispatch_failed", error=str(e))

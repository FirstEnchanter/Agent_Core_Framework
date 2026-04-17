import asyncio
from typing import List, Dict, Any
from executor.tools.email import EmailClient
from executor.tools.transformation import OpenAIClient
from executor.tools.messaging import MessagingClient
from executor.tools.history import TriageHistory
from executor.tools.logging_tool import get_logger

log = get_logger(__name__)

class EmailTriageOrchestrator:
    """
    Main controller for the Email Triage workflow.
    """
    def __init__(self, email_client: EmailClient, ai_client: OpenAIClient, messaging_client: MessagingClient = None, history_client: TriageHistory = None):
        self.email = email_client
        self.ai = ai_client
        self.messaging = messaging_client
        self.history = history_client

    async def run_triage(self, rules: Dict[str, str], use_management: bool = False, folders: List[str] = None, ignore_history: bool = False, progress_callback: Any = None):
        """
        Executes a triage cycle based on provided brand rules.
        """
        log.info("triage.cycle_started", rules_size=len(rules), active_mgmt=use_management, folders=folders, ignore_history=ignore_history)
        
        # 1. Fetch
        if self.email:
            # We fetch more in background mode
            inbox_emails = await asyncio.to_thread(self.email.fetch_latest_emails, folders=folders, limit=20)
        else:
            return []

        total_emails = len(inbox_emails)
        results = []
        for index, mail in enumerate(inbox_emails):
            # 2. Progress Update
            if progress_callback:
                await progress_callback(index + 1, total_emails)

            # 3. Memory Check (Skip seen emails unless ignore_history is True)
            mail_id = mail.get('id', mail['subject']) 
            if not ignore_history and self.history and not self.history.is_new(mail_id):
                continue

            # 3. Judge (The LLM Decision)
            decision = await asyncio.to_thread(self._judge_email, mail, rules)
            
            # Detect API Authentication Failures
            if isinstance(decision, str) and "ERROR_AUTH_FAILED" in decision:
                log.error("triage.halted_due_to_auth")
                if self.messaging:
                    await asyncio.to_thread(self.messaging._send_generic,
                        {"subject": "SYSTEM MAINTENANCE REQUIRED"},
                        {"category": "CRITICAL", "priority": 10, "rationale": "The OpenAI API key is expired or invalid. Triage has been paused until a new key is provided."}
                    )
                break

            # 4. Action Layer (Management)
            if use_management and self.email:
                # Folder Mapping: [Agent]/Category (e.g. Triage/Invoices)
                category = decision.get('category', 'Uncategorized')
                target_folder = f"[Agent]/{category}"
                
                # Move the email
                await asyncio.to_thread(self.email.move_email, mail_id, target_folder)
                
                # Flag if Priority >= 4
                if decision.get('priority', 1) >= 4:
                    # Note: We flag it in the NEW folder since it was moved
                    await asyncio.to_thread(self.email.flag_email, mail_id, folder=target_folder)

            # 5. Notify (Messaging)
            # URGENCY FILTER: Only notify based on dynamic threshold (default to 4)
            threshold = int(rules.get('threshold', 4))
            if self.messaging and decision.get('priority', 1) >= threshold:
                await asyncio.to_thread(self.messaging.send_triage_alert, mail, decision)

            results.append({
                "mail": mail,
                "triage": decision
            })
            
            log.info("triage.decided", 
                     subject=mail['subject'], 
                     category=decision['category'], 
                     priority=decision['priority'])
            
        return results

    def _judge_email(self, mail: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Uses OpenAI to classify the email based on the SME ruleset.
        """
        prompt = f"""
        You are an Administrative AI Agent. 
        Your task is to triage an incoming email.

        --- BRAND RULES (NECESSARY QUESTIONS) ---
        Business Goal: {rules.get('business_goal', 'General Support')}
        VIP List: {rules.get('vips', 'None provided')}
        Urgency Triggers: {rules.get('urgency_triggers', 'None')}
        Tone/Voice: {rules.get('tone', 'Professional')}

        --- EMAIL CONTENT ---
        From: {mail['from']}
        Subject: {mail['subject']}
        Body: {mail['body']}

        --- OUTPUT FORMAT (CRITICAL) ---
        1. "category": (Urgent, Informational, Networking, Promotion, Social, Spam)
        2. "priority": (1-5, 5 being highest)
        3. "rationale": (Concise summary of the email and action. MAX 3 SENTENCES.)
        4. "action": (Forward, Reply, Archive, Flag)
        5. "draft": (Short professional draft if action is Reply)
        
        Respond ONLY in valid JSON.
        """
        
        try:
            response = self.ai.complete(
                prompt, 
                "You are a precise business administrator. Respond only in valid JSON."
            )
            
            # Robust JSON Parser
            import json
            import re
            
            # 1. Clean markdown wrappers
            clean_res = response.strip()
            if clean_res.startswith("```"):
                clean_res = re.sub(r'^```[a-z]*\n', '', clean_res)
                clean_res = re.sub(r'\n```$', '', clean_res)
            
            # 2. Extract first JSON-like block
            match = re.search(r'\{.*\}', clean_res, re.DOTALL)
            if match:
                return json.loads(match.group())
            
            log.error("triage.parse_failed", raw_response=response)
            return {"category": "Unsorted", "priority": 1, "rationale": "The agent provided a judgment but it could not be parsed."}
            
        except Exception as e:
            log.error("triage.judge_failed", error=str(e))
            return {"category": "Error", "priority": 0, "rationale": str(e)}

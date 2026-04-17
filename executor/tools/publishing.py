"""
Publishing / Distribution Tools — Layer 3: Execution

Tool Class 3: Publishing / Distribution Tools (from CLAUDE.md)

Approved channels:
    - Bluesky (post creation)
    - Email systems (SMTP)
    - Content platforms (Substack draft creation)

WARNING: Publishing tools cause external, irreversible side effects.
         These must only be invoked AFTER Brand Alignment Engine clearance.
         Never call publishing tools directly from a directive without
         orchestrator approval.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from executor.tools.logging_tool import get_logger

log = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Bluesky Publisher
# ──────────────────────────────────────────────────────────────────────────────

class BlueSkyPublisher:
    """
    Post content to Bluesky via the AT Protocol.
    """

    BLUESKY_MAX_CHARS = 300

    def __init__(self) -> None:
        self.handle = os.environ.get("BLUESKY_HANDLE", "")
        self.email = os.environ.get("BLUESKY_EMAIL", "")
        self.app_password = os.environ.get("BLUESKY_APP_PASSWORD", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from atproto import Client
            self._client = Client()
            identifier = self.email or self.handle
            self._client.login(identifier, self.app_password)
        return self._client




    def post(
        self,
        text: str,
        reply_to: Optional[str] = None,
        embed_url: Optional[str] = None,
    ) -> dict:
        """
        Create a new post on Bluesky.
        """
        if len(text) > self.BLUESKY_MAX_CHARS:
            raise ValueError(
                f"Post text exceeds Bluesky limit: {len(text)} > {self.BLUESKY_MAX_CHARS} chars"
            )

        client = self._get_client()
        
        # Simple facet detection for links (not exhaustive but handles common cases)
        from atproto import client_utils
        text_builder = client_utils.TextBuilder()
        
        # This is a bit simplified, ideally we parse for URLs
        # But for now, we'll just send as is or use client_utils if we had structured text
        # Let's use the basic send_post which handles simple text. 
        # For links to be clickable, we need facets.
        
        log.info("bluesky.post", text_length=len(text))
        
        # Handle embeds if url is provided
        embed = None
        if embed_url:
            # TODO: Implementation of external card embed requires fetching title/description/thumb
            pass

        try:
            # client.send_post returns a CreatePostResponse which has .uri and .cid
            response = client.send_post(text=text)
            return {"uri": response.uri, "cid": response.cid}
        except Exception as e:
            log.error("bluesky.post_failed", error=str(e))
            raise

    def post_thread(self, posts: list[str]) -> list[dict]:
        """
        Create a thread of posts.
        """
        client = self._get_client()
        results = []
        parent = None
        root = None
        
        for post_text in posts:
            reply_ref = None
            if parent:
                from atproto import models
                reply_ref = models.AppBskyFeedPost.ReplyRef(parent=parent, root=root)
            
            response = client.send_post(text=post_text, reply_to=reply_ref)
            
            from atproto import models
            current_ref = models.ComAtprotoRepoStrongRef.Main(cid=response.cid, uri=response.uri)
            
            if not root:
                root = current_ref
            parent = current_ref
            
            results.append({"uri": response.uri, "cid": response.cid})
            
        return results



# ──────────────────────────────────────────────────────────────────────────────
# Email / Escalation Notifier
# ──────────────────────────────────────────────────────────────────────────────

class EmailNotifier:
    """
    Send email notifications via SMTP.

    Primary use: escalation notifications to the SH steward.
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
    ) -> None:
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
        self.smtp_password = smtp_password or os.environ.get("SMTP_PASSWORD", "")

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: Optional[str] = None,
    ) -> None:
        """
        Send a plain-text email.

        Args:
            to:        Recipient email address.
            subject:   Email subject line.
            body:      Plain text email body.
            from_addr: Sender address (defaults to smtp_user).
        """
        from_addr = from_addr or self.smtp_user

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.attach(MIMEText(body, "plain"))

        log.info("email.send", to=to, subject=subject)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(from_addr, to, msg.as_string())
            log.info("email.sent", to=to)
        except Exception as exc:
            log.error("email.send_failed", to=to, error=str(exc))
            raise

    def notify_escalation(self, subject: str, body: str) -> None:
        """
        Send an escalation notification to the configured steward address.
        """
        escalation_email = os.environ.get("ESCALATION_EMAIL", "")
        if not escalation_email:
            log.warning("email.escalation_skipped", reason="ESCALATION_EMAIL not configured")
            return
        self.send(to=escalation_email, subject=f"[SH Agent Escalation] {subject}", body=body)

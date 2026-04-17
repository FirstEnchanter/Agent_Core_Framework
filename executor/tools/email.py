"""
Email Execution Tools  Layer 3: Execution
Universal IMAP/SMTP Connectivity for Triage.
"""

import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from executor.tools.logging_tool import get_logger

log = get_logger(__name__)

class EmailClient:
    """
    Universal Email Client supporting IMAP (Read) and SMTP (Write).
    Designed to be provider-agnostic.
    """
    def __init__(
        self, 
        imap_server: str, 
        smtp_server: str, 
        email_user: str, 
        email_pass: str,
        imap_port: int = 993,
        smtp_port: int = 587
    ):
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.user = email_user
        self.password = email_pass
        self.imap_port = imap_port
        self.smtp_port = smtp_port

    def fetch_latest_emails(self, folders: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch and parse emails from one or more folders."""
        if folders is None:
            folders = ["INBOX"]
            
        emails = []
        try:
            log.info("email.imap_connect", server=self.imap_server, user=self.user)
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.user, self.password)

            for folder in folders:
                log.info("email.select_folder", folder=folder)
                try:
                    mail.select(folder)
                except:
                    log.warning("email.folder_missing", folder=folder)
                    continue

                # Get IDs of latest emails
                status, messages = mail.search(None, "ALL")
                mail_ids = messages[0].split()
                latest_ids = mail_ids[-limit:]

                for m_id in reversed(latest_ids):
                    status, msg_data = mail.fetch(m_id, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Decode Subject
                            subject_raw = msg.get("Subject")
                            subject_decoded, encoding = decode_header(subject_raw)[0]
                            if isinstance(subject_decoded, bytes):
                                subject = subject_decoded.decode(encoding or 'utf-8', errors='replace')
                            else:
                                subject = subject_decoded

                            sender = msg.get("From")
                            
                            # Get body
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        charset = part.get_content_charset() or 'utf-8'
                                        try:
                                            body = part.get_payload(decode=True).decode(charset, errors='replace')
                                        except:
                                            body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                        break
                            else:
                                charset = msg.get_content_charset() or 'utf-8'
                                try:
                                    body = msg.get_payload(decode=True).decode(charset, errors='replace')
                                except:
                                    body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

                            emails.append({
                                "id": m_id.decode(),
                                "subject": subject,
                                "from": sender,
                                "body": body,
                                "date": msg.get("Date"),
                                "source_folder": folder
                            })
            
            mail.close()
            mail.logout()
            return emails

        except Exception as e:
            log.error("email.fetch_failed", error=str(e))
            raise

    def send_reply(self, to_email: str, subject: str, body: str):
        """Send a professional reply via SMTP."""
        try:
            log.info("email.smtp_connect", server=self.smtp_server, to=to_email)
            msg = MIMEText(body)
            msg["Subject"] = f"Re: {subject}"
            msg["From"] = self.user
            msg["To"] = to_email

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
                
            log.info("email.send_success", to=to_email)
        except Exception as e:
            log.error("email.send_failed", error=str(e))
            raise

    def ensure_folder_exists(self, folder_path: str):
        """Checks if a folder exists, creates it if missing."""
        try:
            log.info("email.check_folder", folder=folder_path)
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.user, self.password)
            
            # Check if folder exists
            status, folders = mail.list()
            # Normalize folder path for comparison
            # Note: Some servers use different delimiters, we assume '/' for now 
            # and search for the folder name in quotes or direct
            exists = any(f'"{folder_path}"' in str(f) or f' {folder_path}' in str(f) for f in folders)
            
            if not exists:
                log.info("email.create_folder", folder=folder_path)
                mail.create(folder_path)
                mail.subscribe(folder_path)
            
            mail.logout()
        except Exception as e:
            log.error("email.folder_ops_failed", error=str(e))

    def move_email(self, email_id: str, target_folder: str, source_folder: str = "INBOX"):
        """Moves an email to a target folder using Copy-Delete-Expunge."""
        try:
            self.ensure_folder_exists(target_folder)
            
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.user, self.password)
            mail.select(source_folder)

            # 1. Copy to target
            log.info("email.move_copy", id=email_id, target=target_folder)
            status, result = mail.uid('COPY', email_id, target_folder)
            
            if status == 'OK':
                # 2. Mark as deleted in source
                log.info("email.move_delete_source", id=email_id)
                mail.uid('STORE', email_id, '+FLAGS', '(\\Deleted)')
                mail.expunge()
            
            mail.logout()
            log.info("email.move_success", id=email_id)
        except Exception as e:
            log.error("email.move_failed", error=str(e))

    def flag_email(self, email_id: str, folder: str = "INBOX"):
        """Stars/Flags an email in the specified folder."""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.user, self.password)
            mail.select(folder)
            
            log.info("email.flag_item", id=email_id)
            mail.uid('STORE', email_id, '+FLAGS', '(\\Flagged)')
            
            mail.logout()
        except Exception as e:
            log.error("email.flag_failed", error=str(e))

"""
Email utilities for monitoring and extracting authentication codes.
"""

import re
import email
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import imaplib
import email.mime.text

logger = logging.getLogger(__name__)


class EmailMonitor:
    """Monitor email for authentication codes and notifications."""
    
    def __init__(self, server: str, port: int, username: str, password: str, use_ssl: bool = True):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to email server."""
        try:
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            else:
                self.connection = imaplib.IMAP4(self.server, self.port)
            
            self.connection.login(self.username, self.password)
            logger.info(f"Connected to email server: {self.server}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from email server."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from email server")
            except:
                pass
            finally:
                self.connection = None
    
    def search_emails(self, folder: str = "INBOX", subject_filter: str = None, 
                     from_filter: str = None, since_hours: int = 24) -> List[Dict[str, Any]]:
        """Search for emails matching criteria."""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            self.connection.select(folder)
            
            # Build search criteria
            criteria = []
            
            if since_hours:
                since_date = (datetime.now() - timedelta(hours=since_hours)).strftime("%d-%b-%Y")
                criteria.append(f'SINCE "{since_date}"')
            
            if subject_filter:
                criteria.append(f'SUBJECT "{subject_filter}"')
            
            if from_filter:
                criteria.append(f'FROM "{from_filter}"')
            
            search_string = " ".join(criteria) if criteria else "ALL"
            
            typ, msg_ids = self.connection.search(None, search_string)
            
            emails = []
            for msg_id in msg_ids[0].split():
                try:
                    typ, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    emails.append({
                        "id": msg_id.decode(),
                        "subject": email_message["Subject"],
                        "from": email_message["From"],
                        "date": email_message["Date"],
                        "body": self._get_email_body(email_message)
                    })
                except Exception as e:
                    logger.error(f"Error processing email {msg_id}: {e}")
            
            return emails
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def _get_email_body(self, email_message) -> str:
        """Extract text body from email message."""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return email_message.get_payload(decode=True).decode()
        return ""
    
    def extract_synthesis_code(self, emails: List[Dict[str, Any]]) -> Optional[str]:
        """Extract Synthesis login code from emails."""
        synthesis_patterns = [
            r"Your verification code is:?\s*([A-Z0-9]{6})",
            r"verification code:?\s*([A-Z0-9]{6})",
            r"login code:?\s*([A-Z0-9]{6})",
            r"code:?\s*([A-Z0-9]{6})",
        ]
        
        # Sort emails by date (newest first)
        sorted_emails = sorted(emails, key=lambda x: x["date"], reverse=True)
        
        for email_data in sorted_emails:
            subject = email_data.get("subject", "").lower()
            body = email_data.get("body", "")
            
            # Check if this looks like a Synthesis email
            if any(keyword in subject for keyword in ["synthesis", "verification", "login"]):
                for pattern in synthesis_patterns:
                    match = re.search(pattern, body, re.IGNORECASE)
                    if match:
                        code = match.group(1)
                        logger.info(f"Found Synthesis code: {code}")
                        return code
        
        return None
    
    def delete_email(self, email_id: str, folder: str = "INBOX"):
        """Delete email by ID (for cleanup after using code)."""
        if not self.connection:
            return False
        
        try:
            self.connection.select(folder)
            self.connection.store(email_id, "+FLAGS", "\\Deleted")
            self.connection.expunge()
            logger.info(f"Deleted email {email_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting email {email_id}: {e}")
            return False


class SynthesisEmailMonitor(EmailMonitor):
    """Specialized email monitor for Synthesis.com authentication."""
    
    def get_latest_login_code(self) -> Optional[str]:
        """Get the latest Synthesis login code from email."""
        emails = self.search_emails(
            subject_filter="verification",
            since_hours=1  # Only check last hour
        )
        
        return self.extract_synthesis_code(emails)
    
    def cleanup_old_codes(self):
        """Clean up old verification emails to prevent clutter."""
        emails = self.search_emails(
            subject_filter="verification",
            since_hours=24
        )
        
        # Delete emails older than 1 hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        for email_data in emails:
            try:
                email_date = datetime.strptime(email_data["date"], "%a, %d %b %Y %H:%M:%S %z")
                if email_date.replace(tzinfo=None) < one_hour_ago:
                    self.delete_email(email_data["id"])
            except Exception as e:
                logger.error(f"Error processing email date: {e}")
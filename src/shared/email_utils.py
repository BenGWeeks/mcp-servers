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
        # Updated patterns based on actual Synthesis email format
        synthesis_patterns = [
            r"Here's your log in verification code:\s*(\d{4})",  # Main pattern from samples
            r"verification code:\s*(\d{4})",
            r"login code:\s*(\d{4})",
            r"code:\s*(\d{4})",
            r"\b(\d{4})\b",  # Fallback: any 4-digit number
        ]
        
        # Sort emails by date (newest first)
        sorted_emails = sorted(emails, key=lambda x: x["date"], reverse=True)
        
        for email_data in sorted_emails:
            subject = email_data.get("subject", "").lower()
            body = email_data.get("body", "")
            from_addr = email_data.get("from", "").lower()
            
            # Check if this looks like a Synthesis login email
            if ("login for synthesis" in subject or 
                "synthesis" in subject and "login" in subject or
                "teams@synthesis.com" in from_addr):
                
                for pattern in synthesis_patterns:
                    match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                    if match:
                        code = match.group(1)
                        # Verify it's a 4-digit code
                        if len(code) == 4 and code.isdigit():
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
    """Specialized email monitor for Synthesis.com authentication and progress tracking."""
    
    def get_latest_login_code(self) -> Optional[str]:
        """Get the latest Synthesis login code from email."""
        emails = self.search_emails(
            subject_filter="Login for Synthesis",
            since_hours=1  # Only check last hour - removed from_filter to support forwarded emails
        )
        
        return self.extract_synthesis_code(emails)
    
    def get_recent_login_codes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent login codes with timestamps."""
        emails = self.search_emails(
            subject_filter="Login for Synthesis",
            since_hours=24  # Removed from_filter to support forwarded emails
        )
        
        codes = []
        for email_data in emails[:limit]:
            code = self.extract_synthesis_code([email_data])
            if code:
                codes.append({
                    "code": code,
                    "date": email_data["date"],
                    "email_id": email_data["id"]
                })
        
        return codes
    
    def get_progress_emails(self, since_hours: int = 24) -> List[Dict[str, Any]]:
        """Get progress and session emails from Synthesis."""
        # Search for different types of progress emails
        all_emails = []
        
        # Progress summary emails
        progress_emails = self.search_emails(
            subject_filter="progress with Synthesis",
            since_hours=since_hours  # Removed from_filter to support forwarded emails
        )
        all_emails.extend(progress_emails)
        
        # Session emails  
        session_emails = self.search_emails(
            subject_filter="Synthesis Session",
            since_hours=since_hours  # Removed from_filter to support forwarded emails
        )
        all_emails.extend(session_emails)
        
        # Parse and extract data from emails
        parsed_emails = []
        for email_data in all_emails:
            parsed = self._parse_progress_email(email_data)
            if parsed:
                parsed_emails.append(parsed)
        
        return parsed_emails
    
    def get_newsletter_emails(self, since_hours: int = 168) -> List[Dict[str, Any]]:
        """Get weekly newsletter emails about upcoming Synthesis activities."""
        # Weekly newsletter emails
        newsletters = self.search_emails(
            subject_filter="This Week at Synthesis",
            since_hours=since_hours  # Check last week - removed from_filter to support forwarded emails
        )
        
        # Return newsletters with minimal parsing - just for AI context
        parsed_newsletters = []
        for email_data in newsletters:
            parsed_newsletters.append({
                "subject": email_data.get("subject", ""),
                "date": email_data.get("date", ""),
                "type": "newsletter",
                "content": email_data.get("body", "")[:1000],  # First 1000 chars
                "full_content": email_data.get("body", "")
            })
        
        return parsed_newsletters
    
    def get_payment_emails(self, since_hours: int = 720) -> List[Dict[str, Any]]:
        """Get payment confirmation emails for subscription tracking."""
        # Payment confirmation emails (check last 30 days)
        payments = self.search_emails(
            subject_filter="Payment Confirmation for Synthesis",
            since_hours=since_hours  # Removed from_filter to support forwarded emails
        )
        
        # Parse payment emails
        parsed_payments = []
        for email_data in payments:
            parsed = self._parse_payment_email(email_data)
            if parsed:
                parsed_payments.append(parsed)
        
        return parsed_payments
    
    def _parse_progress_email(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a progress email to extract study data."""
        try:
            subject = email_data.get("subject", "")
            body = email_data.get("body", "")
            
            # Extract student name
            student_match = re.search(r"(\w+)'s (?:progress|Synthesis Session)", subject)
            student_name = student_match.group(1) if student_match else None
            
            # Extract study minutes
            minutes_patterns = [
                r"Daily Active Minutes\s*(\d+)",  # Check this first for weekly totals
                r"(\d+\.?\d*)\s*minutes",
                r"(\d+\.?\d*)\s*MINUTES",
            ]
            
            study_minutes = 0
            for pattern in minutes_patterns:
                match = re.search(pattern, body)
                if match:
                    study_minutes = float(match.group(1))
                    break
            
            # Extract activities/lessons
            activities = []
            
            # Look for lesson titles in specific formats
            lesson_patterns = [
                r"(?:worked on|completed|explored)\s+[\"']([^\"']+)[\"']",
                r"session:\s*([^\n]+)",
                r"Activities?\s*\n+([^\n]+)",
            ]
            
            for pattern in lesson_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                activities.extend(matches)
            
            # Also look for lessons in the weekly format "Lesson Name\n\nCategory\n\nX minutes"
            weekly_lesson_pattern = r"([A-Z][^\n]+)\n\n[^\n]+\n\n\d+\.?\d*\s*minutes"
            weekly_matches = re.findall(weekly_lesson_pattern, body)
            for match in weekly_matches:
                if match.strip() and match.strip() not in activities:
                    activities.append(match.strip())
            
            # Extract achievements if present
            achievements = []
            # Look for specific known achievements
            known_achievements = ["Treasure Seeker", "Rising Star", "Gold Digger", 
                                "Speed Demon", "Perfect Score", "Math Master"]
            for achievement in known_achievements:
                if achievement in body:
                    achievements.append(achievement)
            
            return {
                "subject": subject,
                "date": email_data["date"],
                "student_name": student_name,
                "study_minutes": study_minutes,
                "activities": activities,
                "achievements": achievements,
                "content": body[:500],  # First 500 chars for reference
            }
            
        except Exception as e:
            logger.error(f"Error parsing progress email: {e}")
            return None
    
    def _parse_payment_email(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a payment confirmation email to extract billing data."""
        try:
            subject = email_data.get("subject", "")
            body = email_data.get("body", "")
            
            # Extract payment amount
            amount_patterns = [
                r"payment of \$(\d+(?:\.\d{2})?)",
                r"\$(\d+(?:\.\d{2})?) has been processed",
                r"amount.*?\$(\d+(?:\.\d{2})?)",
            ]
            
            amount = None
            for pattern in amount_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    amount = float(match.group(1))
                    break
            
            # Extract plan type
            plan_patterns = [
                r"(Tutor Monthly|Tutor Annual|Premium|Basic)",
                r"Your ([^\\s]+) payment",
            ]
            
            plan_type = None
            for pattern in plan_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    plan_type = match.group(1)
                    break
            
            # Extract invoice URL
            invoice_url = None
            invoice_match = re.search(r"https://invoice\.stripe\.com/[^\\s\"'<>]+", body)
            if invoice_match:
                invoice_url = invoice_match.group(0)
            
            return {
                "subject": subject,
                "date": email_data["date"],
                "type": "payment",
                "amount": amount,
                "plan_type": plan_type,
                "invoice_url": invoice_url,
                "content": body[:500],  # First 500 chars for reference
            }
            
        except Exception as e:
            logger.error(f"Error parsing payment email: {e}")
            return None
    
    def cleanup_old_codes(self):
        """Clean up old verification emails to prevent clutter."""
        emails = self.search_emails(
            subject_filter="Login for Synthesis",
            since_hours=48  # Removed from_filter to support forwarded emails
        )
        
        # Delete emails older than 2 hours
        two_hours_ago = datetime.now() - timedelta(hours=2)
        
        for email_data in emails:
            try:
                # Parse various date formats
                date_str = email_data["date"]
                # Try different date parsing strategies
                for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"]:
                    try:
                        email_date = datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue
                else:
                    # If no format works, skip
                    continue
                    
                if email_date.replace(tzinfo=None) < two_hours_ago:
                    self.delete_email(email_data["id"])
                    logger.info(f"Deleted old login code email from {date_str}")
                    
            except Exception as e:
                logger.error(f"Error processing email cleanup: {e}")
    
    def test_connection(self) -> bool:
        """Test email connection and return status."""
        return self.connect()
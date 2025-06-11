#!/usr/bin/env python3
"""
Simplified Synthesis MCP Server - Email-only, no database
Returns raw email data for AI interpretation
"""

import asyncio
import json
import logging
import os
import sys
import imaplib
import email
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from email.header import decode_header

# Setup logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


class SimpleEmailMonitor:
    """Simplified email monitor - just fetch and return emails"""
    
    def __init__(self, server: str, port: int, username: str, password: str):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            self.connection = imaplib.IMAP4(self.server, self.port)
            self.connection.login(self.username, self.password)
            logger.info("Connected to email server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def search_emails(self, subject_contains: str = None, from_contains: str = None, 
                     since_days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Search emails with filters"""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            self.connection.select('INBOX')
            
            # Build search criteria
            criteria = []
            since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
            criteria.append(f'SINCE "{since_date}"')
            
            if subject_contains:
                criteria.append(f'SUBJECT "{subject_contains}"')
            if from_contains:
                criteria.append(f'FROM "{from_contains}"')
            
            search_string = ' '.join(criteria) if criteria else 'ALL'
            typ, msg_ids = self.connection.search(None, search_string)
            
            if typ != 'OK':
                return []
            
            # Get emails (newest first)
            email_ids = msg_ids[0].split()
            email_ids.reverse()
            
            emails = []
            for msg_id in email_ids[:limit]:
                try:
                    typ, msg_data = self.connection.fetch(msg_id, '(RFC822)')
                    if typ != 'OK':
                        continue
                        
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Decode subject
                    subject = email_message['Subject']
                    if subject:
                        decoded_subject = decode_header(subject)[0]
                        if isinstance(decoded_subject[0], bytes):
                            subject = decoded_subject[0].decode(decoded_subject[1] or 'utf-8')
                        else:
                            subject = decoded_subject[0]
                    
                    # Get text body
                    body = self._get_email_body(email_message)
                    
                    emails.append({
                        "id": msg_id.decode(),
                        "subject": subject or "No Subject",
                        "from": email_message['From'] or "Unknown",
                        "date": email_message['Date'] or "Unknown",
                        "body": body,
                        "preview": body[:200] + "..." if len(body) > 200 else body
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing email {msg_id}: {e}")
            
            return emails
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def _get_email_body(self, email_message) -> str:
        """Extract text body from email"""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode('utf-8', errors='replace')
                    except:
                        return part.get_payload()
        else:
            try:
                return email_message.get_payload(decode=True).decode('utf-8', errors='replace')
            except:
                return email_message.get_payload()
        return ""


class SimpleSynthesisMCPServer:
    """Simplified MCP server - no database, just email fetching"""
    
    def __init__(self):
        self.server_info = {
            "name": "synthesis",
            "version": "2.0.0",
            "description": "Email integration for Synthesis.com education tracking. Monitors study progress, login codes, and subscriptions for the Weeks family."
        }
        
        # Initialize email monitor
        try:
            self.email_monitor = SimpleEmailMonitor(
                server=os.getenv('EMAIL_SERVER', 'protonmail-bridge'),
                port=int(os.getenv('EMAIL_PORT', '143')),
                username=os.getenv('EMAIL_USERNAME', ''),
                password=os.getenv('EMAIL_PASSWORD', '')
            )
            logger.info("Email monitor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize email monitor: {e}")
            self.email_monitor = None
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP messages"""
        method = message.get('method')
        params = message.get('params', {})
        msg_id = message.get('id')
        
        logger.info(f"Processing method: {method}")
        
        try:
            if method == "initialize":
                response = await self._handle_initialize(params)
            elif method == "tools/list":
                response = await self._handle_list_tools(params)
            elif method == "tools/call":
                response = await self._handle_call_tool(params)
            else:
                response = {
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            # Add id and jsonrpc
            if msg_id is not None:
                response["id"] = msg_id
            response["jsonrpc"] = "2.0"
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            if msg_id is not None:
                error_response["id"] = msg_id
            return error_response
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": self.server_info
            }
        }
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                "name": "get_study_progress",
                "description": "Get Synthesis.com study session emails. These arrive after each study session (typically 2-4 times per week). Each email contains session duration, achievements earned, and activities completed. Synthesis is an AI-powered online learning platform with collaborative games for children ages 8-14.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Number of emails to return (max: 50)"
                        },
                        "since_days": {
                            "type": "integer",
                            "default": 7,
                            "description": "Days to look back (sessions are 2-4x/week, so 7 days usually captures a full week)"
                        }
                    }
                }
            },
            {
                "name": "get_login_codes",
                "description": "Get Synthesis login verification emails containing 4-digit codes. These are sent on-demand when logging in (frequency varies). Codes expire after 2 hours. Only request recent emails (1-2 days) unless specifically looking for historical logins.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 1,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Number of emails to return (usually only need the most recent)"
                        },
                        "since_days": {
                            "type": "integer",
                            "default": 1,
                            "description": "Days to look back (codes expire quickly, so recent is best)"
                        }
                    }
                }
            },
            {
                "name": "get_subscription_status",
                "description": "Get Synthesis payment and subscription emails. These arrive monthly for subscriptions or when payments are processed. Check 35-40 days back to ensure capturing the last payment.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Number of emails to return"
                        },
                        "since_days": {
                            "type": "integer",
                            "default": 35,
                            "description": "Days to look back (payments are monthly, so 35 days ensures we see the last one)"
                        }
                    }
                }
            },
            {
                "name": "get_synthesis_newsletter",
                "description": "Get 'This Week at Synthesis' newsletters with upcoming activities and educational content. These arrive weekly on Mondays. Look back 14 days to see the last 2 newsletters.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 2,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Number of emails to return"
                        },
                        "since_days": {
                            "type": "integer",
                            "default": 14,
                            "description": "Days to look back (newsletters are weekly, so 14 days = 2 newsletters)"
                        }
                    }
                }
            },
            {
                "name": "get_any_email",
                "description": "Search for any email by subject or sender. Useful for finding specific communications like CEO updates, special announcements, or non-standard emails. Consider email frequency when setting since_days.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "subject_contains": {
                            "type": "string",
                            "description": "Text to search for in subject (case-insensitive)"
                        },
                        "from_contains": {
                            "type": "string",
                            "description": "Text to search for in sender (e.g., 'CEO', '@synthesis.com')"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Number of emails to return"
                        },
                        "since_days": {
                            "type": "integer",
                            "default": 30,
                            "description": "Days to look back"
                        }
                    }
                }
            }
        ]
        
        return {"result": {"tools": tools}}
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        logger.info(f"Calling tool: {tool_name} with args: {arguments}")
        
        if not self.email_monitor:
            return {
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "error": "Email monitoring not available",
                            "emails": [],
                            "count": 0
                        })
                    }]
                }
            }
        
        # Enforce max limit
        limit = min(arguments.get('limit', 10), 50)
        since_days = arguments.get('since_days', 7)
        
        try:
            if tool_name == "get_study_progress":
                emails = self.email_monitor.search_emails(
                    subject_contains="Synthesis Session",
                    since_days=since_days,
                    limit=limit
                )
            elif tool_name == "get_login_codes":
                emails = self.email_monitor.search_emails(
                    subject_contains="Login for Synthesis",
                    since_days=since_days,
                    limit=limit
                )
            elif tool_name == "get_subscription_status":
                emails = self.email_monitor.search_emails(
                    subject_contains="Payment Confirmation",
                    since_days=since_days,
                    limit=limit
                )
            elif tool_name == "get_synthesis_newsletter":
                emails = self.email_monitor.search_emails(
                    subject_contains="This Week at Synthesis",
                    since_days=since_days,
                    limit=limit
                )
            elif tool_name == "get_any_email":
                emails = self.email_monitor.search_emails(
                    subject_contains=arguments.get('subject_contains'),
                    from_contains=arguments.get('from_contains'),
                    since_days=since_days,
                    limit=limit
                )
            else:
                return {
                    "error": {
                        "code": -32602,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
            
            # Format response as human-readable text
            if not emails:
                if tool_name == "get_login_codes":
                    response_text = f"No login codes found in the last {since_days} days. Try checking for recent 'Login for Synthesis' emails."
                elif tool_name == "get_study_progress":
                    response_text = f"No study session emails found in the last {since_days} days."
                elif tool_name == "get_subscription_status":
                    response_text = f"No payment emails found in the last {since_days} days."
                elif tool_name == "get_synthesis_newsletter":
                    response_text = f"No newsletter emails found in the last {since_days} days."
                else:
                    response_text = f"No emails found matching your criteria in the last {since_days} days."
            else:
                response_text = f"Found {len(emails)} email(s) from the last {since_days} days:\n\n"
                
                for i, email in enumerate(emails, 1):
                    response_text += f"**Email {i}:**\n"
                    response_text += f"Subject: {email['subject']}\n"
                    response_text += f"From: {email['from']}\n"
                    response_text += f"Date: {email['date']}\n"
                    response_text += f"Preview: {email['preview']}\n"
                    
                    # For login codes, try to extract the code
                    if tool_name == "get_login_codes" and email['body']:
                        import re
                        code_patterns = [
                            r"Here's your log in verification code:\s*(\d{4})",
                            r"verification code:\s*(\d{4})",
                            r"login code:\s*(\d{4})",
                            r"code:\s*(\d{4})",
                            r"\b(\d{4})\b"
                        ]
                        for pattern in code_patterns:
                            match = re.search(pattern, email['body'], re.IGNORECASE)
                            if match:
                                response_text += f"**LOGIN CODE: {match.group(1)}**\n"
                                break
                    
                    response_text += "\n" + "="*50 + "\n\n"
            
            return {
                "result": {
                    "content": [{
                        "type": "text",
                        "text": response_text
                    }]
                }
            }
            
        except Exception as e:
            logger.error(f"Error in tool {tool_name}: {e}", exc_info=True)
            return {
                "error": {
                    "code": -32603,
                    "message": f"Tool execution error: {str(e)}"
                }
            }
    
    async def run(self):
        """Main server loop"""
        logger.info("Starting simplified MCP server")
        
        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    message = json.loads(line)
                    response = await self.handle_message(message)
                    print(json.dumps(response), flush=True)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    server = SimpleSynthesisMCPServer()
    asyncio.run(server.run())
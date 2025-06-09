"""
MCP server for Synthesis.com study tracking integration.
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from mcp.types import Tool, TextContent

# Local imports
import sys
import os
# Add the src directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.mcp_base import MCPBaseServer, create_tool
from shared.email_utils import SynthesisEmailMonitor
from shared.storage_utils import StudyProgressDB
from synthesis.synthesis_client import SynthesisClient
from synthesis.config import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SynthesisTrackerServer(MCPBaseServer):
    """MCP server for tracking Synthesis.com study progress."""
    
    def __init__(self):
        super().__init__("synthesis-tracker", "1.0.0")
        
        # Initialize components
        self.email_monitor = SynthesisEmailMonitor(
            server=config.email_server,
            port=config.email_port,
            username=config.email_username,
            password=config.email_password,
            use_ssl=config.email_use_ssl
        )
        
        self.db = StudyProgressDB(config.database_path)
        
        logger.info("Synthesis Tracker MCP server initialized")
    
    async def get_tools(self) -> List[Tool]:
        """Return available MCP tools."""
        return [
            create_tool(
                name="check_synthesis_login",
                description="Check if user has logged into Synthesis.com today",
                parameters={}
            ),
            create_tool(
                name="get_study_progress",
                description="Get detailed study progress for today or specific date",
                parameters={
                    "date": {
                        "type": "string",
                        "description": "Date to check (YYYY-MM-DD), defaults to today"
                    }
                }
            ),
            create_tool(
                name="get_weekly_summary",
                description="Get weekly study summary and statistics",
                parameters={}
            ),
            create_tool(
                name="send_study_reminder",
                description="Send a study reminder if user hasn't studied today",
                parameters={
                    "custom_message": {
                        "type": "string", 
                        "description": "Custom reminder message (optional)"
                    }
                }
            ),
            create_tool(
                name="get_current_streak",
                description="Get current study streak in days",
                parameters={}
            ),
            create_tool(
                name="force_update_progress",
                description="Force update study progress by logging into Synthesis.com",
                parameters={}
            )
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Handle tool execution."""
        try:
            if name == "check_synthesis_login":
                return await self._check_synthesis_login()
            
            elif name == "get_study_progress":
                date = arguments.get("date")
                return await self._get_study_progress(date)
            
            elif name == "get_weekly_summary":
                return await self._get_weekly_summary()
            
            elif name == "send_study_reminder":
                custom_message = arguments.get("custom_message")
                return await self._send_study_reminder(custom_message)
            
            elif name == "get_current_streak":
                return await self._get_current_streak()
            
            elif name == "force_update_progress":
                return await self._force_update_progress()
            
            else:
                return f"Unknown tool: {name}"
                
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return f"Error: {str(e)}"
    
    async def _check_synthesis_login(self) -> Dict[str, Any]:
        """Check if user logged into Synthesis today."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            session = self.db.get_study_session(today)
            
            has_studied = self.db.has_studied_today()
            
            if session:
                return {
                    "logged_in_today": session.get("logged_in", False),
                    "study_minutes": session.get("study_minutes", 0),
                    "has_studied": has_studied,
                    "last_check": session.get("updated_at"),
                    "streak": self.db.get_current_streak()
                }
            else:
                return {
                    "logged_in_today": False,
                    "study_minutes": 0,
                    "has_studied": False,
                    "last_check": None,
                    "streak": self.db.get_current_streak()
                }
                
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return {"error": str(e)}
    
    async def _get_study_progress(self, date: str = None) -> Dict[str, Any]:
        """Get detailed study progress."""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            session = self.db.get_study_session(date)
            
            if session:
                return {
                    "date": session["date"],
                    "logged_in": session.get("logged_in", False),
                    "login_time": session.get("login_time"),
                    "study_minutes": session.get("study_minutes", 0),
                    "lessons_completed": session.get("lessons_completed", []),
                    "last_activity": session.get("last_activity"),
                    "streak_days": session.get("streak_days", 0),
                    "total_points": session.get("total_points", 0),
                    "updated_at": session.get("updated_at")
                }
            else:
                return {
                    "date": date,
                    "logged_in": False,
                    "study_minutes": 0,
                    "lessons_completed": [],
                    "message": "No study session recorded for this date"
                }
                
        except Exception as e:
            logger.error(f"Error getting study progress: {e}")
            return {"error": str(e)}
    
    async def _get_weekly_summary(self) -> Dict[str, Any]:
        """Get weekly study summary."""
        try:
            stats = self.db.get_weekly_stats()
            current_streak = self.db.get_current_streak()
            
            # Calculate additional metrics
            goal_minutes = config.study_goal_minutes * 7  # Weekly goal
            total_minutes = stats.get("total_minutes", 0)
            goal_progress = (total_minutes / goal_minutes * 100) if goal_minutes > 0 else 0
            
            return {
                "week_summary": stats,
                "current_streak": current_streak,
                "weekly_goal_minutes": goal_minutes,
                "goal_progress_percent": min(100, round(goal_progress, 1)),
                "days_this_week": stats.get("days_logged_in", 0),
                "average_session": round(stats.get("avg_minutes", 0), 1),
                "recommendations": self._generate_recommendations(stats, current_streak)
            }
            
        except Exception as e:
            logger.error(f"Error getting weekly summary: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self, stats: Dict[str, Any], streak: int) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []
        
        avg_minutes = stats.get("avg_minutes", 0)
        days_logged = stats.get("days_logged_in", 0)
        
        if days_logged < 5:
            recommendations.append("Try to study at least 5 days this week for better consistency!")
        
        if avg_minutes < config.minimum_study_minutes:
            recommendations.append(f"Aim for at least {config.minimum_study_minutes} minutes per session.")
        
        if streak >= 7:
            recommendations.append(f"Amazing! You're on a {streak}-day streak! Keep it going!")
        elif streak >= 3:
            recommendations.append(f"Great {streak}-day streak! Try to reach a week!")
        
        if not recommendations:
            recommendations.append("You're doing great! Keep up the consistent study habits!")
        
        return recommendations
    
    async def _send_study_reminder(self, custom_message: str = None) -> Dict[str, Any]:
        """Send study reminder if needed."""
        try:
            has_studied = self.db.has_studied_today()
            
            if has_studied:
                return {
                    "reminder_sent": False,
                    "message": "User has already studied today - no reminder needed!"
                }
            
            # Check if we've already sent reminders today
            today_notifications = self.db.get_todays_notifications()
            reminder_count = len([n for n in today_notifications if n["notification_type"] == "reminder"])
            
            if reminder_count >= 3:
                return {
                    "reminder_sent": False,
                    "message": "Maximum daily reminders already sent"
                }
            
            # Generate reminder message
            streak = self.db.get_current_streak()
            
            if custom_message:
                message = custom_message
            else:
                messages = [
                    "Time for some Synthesis math practice! 🧮",
                    "Ready to boost your math skills today? 📚",
                    "Your brain is ready for some number crunching! 🤓",
                    f"Keep that {streak}-day streak going! 🔥" if streak > 0 else "Start a new study streak today! ⭐"
                ]
                
                # Choose message based on time of day
                hour = datetime.now().hour
                if hour < 12:
                    message = "Good morning! " + messages[0]
                elif hour < 17:
                    message = "Afternoon math time! " + messages[1]
                else:
                    message = "Evening study session? " + messages[2]
            
            # Save notification
            self.db.save_notification("reminder", message)
            
            return {
                "reminder_sent": True,
                "message": message,
                "current_streak": streak,
                "todays_reminder_count": reminder_count + 1
            }
            
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return {"error": str(e)}
    
    async def _get_current_streak(self) -> Dict[str, Any]:
        """Get current study streak."""
        try:
            streak = self.db.get_current_streak()
            recent_sessions = self.db.get_recent_sessions(7)
            
            return {
                "current_streak": streak,
                "recent_activity": [
                    {
                        "date": s["date"],
                        "studied": s.get("logged_in", False) and s.get("study_minutes", 0) > 0,
                        "minutes": s.get("study_minutes", 0)
                    }
                    for s in recent_sessions
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting streak: {e}")
            return {"error": str(e)}
    
    async def _force_update_progress(self) -> Dict[str, Any]:
        """Force update by logging into Synthesis and scraping data."""
        try:
            logger.info("Starting forced progress update...")
            
            # Get login code from email
            login_code = self.email_monitor.get_latest_login_code()
            
            if not login_code:
                return {
                    "success": False,
                    "message": "No login code found in email. Please ensure email forwarding is setup correctly."
                }
            
            # Login and scrape data
            async with SynthesisClient(headless=config.headless_browser) as client:
                login_success = await client.login(config.synthesis_email, login_code)
                
                if not login_success:
                    return {
                        "success": False,
                        "message": "Failed to login to Synthesis.com"
                    }
                
                # Get progress data
                progress_data = await client.get_study_progress()
                
                # Save to database
                self.db.save_study_session(progress_data)
                
                # Clean up email
                self.email_monitor.cleanup_old_codes()
                
                return {
                    "success": True,
                    "message": "Successfully updated progress from Synthesis.com",
                    "data": {
                        "study_minutes": progress_data.get("study_time_minutes", 0),
                        "lessons_completed": len(progress_data.get("lessons_completed", [])),
                        "last_activity": progress_data.get("last_activity"),
                        "streak_days": progress_data.get("streak_days", 0)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in forced update: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def main():
    """Run the MCP server."""
    server = SynthesisTrackerServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
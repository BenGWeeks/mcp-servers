"""
Notification utilities for sending push notifications and reminders.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import httpx

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manage push notifications and reminders."""
    
    def __init__(self, webui_url: str = None, api_key: str = None):
        self.webui_url = webui_url or "http://localhost:8080"
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    async def send_push_notification(self, title: str, message: str, 
                                   user_id: str = None, tag: str = "study") -> bool:
        """Send push notification via Open WebUI."""
        try:
            if not self.session:
                self.session = httpx.AsyncClient()
            
            # Open WebUI notification endpoint (if available)
            # This is a placeholder - actual implementation depends on Open WebUI API
            notification_data = {
                "title": title,
                "message": message,
                "tag": tag,
                "timestamp": datetime.now().isoformat()
            }
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Try to send via Open WebUI API
            try:
                response = await self.session.post(
                    f"{self.webui_url}/api/v1/notifications",
                    json=notification_data,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Push notification sent: {title}")
                    return True
                else:
                    logger.warning(f"Notification API returned {response.status_code}")
                    
            except Exception as e:
                logger.debug(f"Push notification not available: {e}")
            
            # Fallback: Log notification for manual delivery
            logger.info(f"NOTIFICATION: {title} - {message}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def send_chat_message(self, message: str, user_id: str = None, 
                               agent_name: str = "Whiskers") -> bool:
        """Send a message through the AI chat interface."""
        try:
            if not self.session:
                self.session = httpx.AsyncClient()
            
            # Prepare chat message
            chat_data = {
                "message": message,
                "agent": agent_name,
                "timestamp": datetime.now().isoformat(),
                "type": "proactive_message"
            }
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Try to send via Open WebUI chat API
            try:
                response = await self.session.post(
                    f"{self.webui_url}/api/v1/chat/send",
                    json=chat_data,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Chat message sent from {agent_name}")
                    return True
                    
            except Exception as e:
                logger.debug(f"Chat API not available: {e}")
            
            # Fallback: Log message
            logger.info(f"CHAT MESSAGE ({agent_name}): {message}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            return False
    
    def format_study_reminder(self, streak: int = 0, custom_message: str = None) -> Dict[str, str]:
        """Format study reminder message."""
        if custom_message:
            return {
                "title": "Study Reminder",
                "message": custom_message
            }
        
        hour = datetime.now().hour
        
        if hour < 12:
            time_greeting = "Good morning"
            emoji = "🌅"
        elif hour < 17:
            time_greeting = "Good afternoon"
            emoji = "☀️"
        else:
            time_greeting = "Good evening"
            emoji = "🌙"
        
        if streak > 0:
            title = f"Keep Your {streak}-Day Streak Going! {emoji}"
            messages = [
                f"You're doing amazing with your {streak}-day study streak! Ready for some Synthesis math?",
                f"Don't break that awesome {streak}-day streak! Time for today's math practice.",
                f"Your {streak}-day streak is impressive! Let's add another day with some Synthesis lessons."
            ]
        else:
            title = f"{time_greeting}! Time to Study {emoji}"
            messages = [
                "Ready to start a new study streak? Let's tackle some math problems!",
                "Your brain is ready for some number crunching! Open up Synthesis and let's go!",
                "Time to boost those math skills! A quick Synthesis session will do wonders."
            ]
        
        # Choose message based on streak
        import random
        message = random.choice(messages)
        
        return {
            "title": title,
            "message": message
        }
    
    def format_achievement_notification(self, achievement_type: str, 
                                      value: Any = None) -> Dict[str, str]:
        """Format achievement notification."""
        achievements = {
            "new_streak": {
                "title": f"🔥 New {value}-Day Streak!",
                "message": f"Congratulations! You've built a {value}-day study streak. Keep it going!"
            },
            "weekly_goal": {
                "title": "🎯 Weekly Goal Achieved!",
                "message": f"Amazing! You've completed your weekly study goal of {value} minutes!"
            },
            "milestone": {
                "title": f"🏆 Milestone Reached!",
                "message": f"Fantastic! You've reached {value} total study minutes!"
            },
            "perfect_week": {
                "title": "⭐ Perfect Week!",
                "message": "Incredible! You studied every single day this week!"
            }
        }
        
        return achievements.get(achievement_type, {
            "title": "🎉 Achievement Unlocked!",
            "message": "Great job on your progress!"
        })
    
    def format_progress_summary(self, stats: Dict[str, Any]) -> str:
        """Format progress summary message."""
        total_minutes = stats.get("total_minutes", 0)
        days_logged = stats.get("days_logged_in", 0)
        streak = stats.get("current_streak", 0)
        
        summary_parts = []
        
        if days_logged > 0:
            summary_parts.append(f"📚 This week: {days_logged} days, {total_minutes} minutes")
        
        if streak > 0:
            summary_parts.append(f"🔥 Current streak: {streak} days")
        
        if total_minutes >= 150:  # Good weekly total
            summary_parts.append("🌟 Excellent progress this week!")
        elif total_minutes >= 90:
            summary_parts.append("👍 Good work this week!")
        else:
            summary_parts.append("💪 Let's aim for more study time!")
        
        return " • ".join(summary_parts)


class ScheduledNotifications:
    """Handle scheduled notifications and reminders."""
    
    def __init__(self, notification_manager: NotificationManager, 
                 db_manager, notification_times: List[str] = None):
        self.notification_manager = notification_manager
        self.db_manager = db_manager
        self.notification_times = notification_times or ["09:00", "15:00", "19:00"]
        self.running = False
    
    async def start_scheduler(self):
        """Start the notification scheduler."""
        self.running = True
        logger.info("Starting notification scheduler")
        
        while self.running:
            try:
                await self._check_and_send_notifications()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in notification scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop_scheduler(self):
        """Stop the notification scheduler."""
        self.running = False
        logger.info("Stopping notification scheduler")
    
    async def _check_and_send_notifications(self):
        """Check if notifications should be sent."""
        try:
            current_time = datetime.now().strftime("%H:%M")
            
            # Check if it's a notification time
            if current_time not in self.notification_times:
                return
            
            # Check if user has studied today
            has_studied = self.db_manager.has_studied_today()
            
            if has_studied:
                logger.debug("User has already studied today, no reminder needed")
                return
            
            # Check if we've already sent a notification at this time today
            today_notifications = self.db_manager.get_todays_notifications()
            current_hour = datetime.now().hour
            
            hourly_notifications = [
                n for n in today_notifications 
                if n["notification_type"] == "reminder" and 
                datetime.fromisoformat(n["sent_at"]).hour == current_hour
            ]
            
            if hourly_notifications:
                logger.debug("Already sent notification this hour")
                return
            
            # Send reminder
            streak = self.db_manager.get_current_streak()
            reminder_data = self.notification_manager.format_study_reminder(streak)
            
            success = await self.notification_manager.send_push_notification(
                title=reminder_data["title"],
                message=reminder_data["message"],
                tag="study_reminder"
            )
            
            if success:
                self.db_manager.save_notification(
                    "reminder", 
                    f"{reminder_data['title']}: {reminder_data['message']}"
                )
                logger.info(f"Sent scheduled reminder at {current_time}")
            
        except Exception as e:
            logger.error(f"Error checking notifications: {e}")
    
    async def send_achievement_notification(self, achievement_type: str, value: Any = None):
        """Send achievement notification."""
        try:
            achievement_data = self.notification_manager.format_achievement_notification(
                achievement_type, value
            )
            
            success = await self.notification_manager.send_push_notification(
                title=achievement_data["title"],
                message=achievement_data["message"],
                tag="achievement"
            )
            
            if success:
                self.db_manager.save_notification(
                    "achievement",
                    f"{achievement_data['title']}: {achievement_data['message']}"
                )
                logger.info(f"Sent achievement notification: {achievement_type}")
            
        except Exception as e:
            logger.error(f"Error sending achievement notification: {e}")
"""
Background scheduler for automated Synthesis.com data collection.
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime
from threading import Thread
from typing import Optional

# Local imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.email_utils import SynthesisEmailMonitor
from shared.storage_utils import StudyProgressDB
from synthesis.synthesis_client import SynthesisClient
from synthesis.config import config

logger = logging.getLogger(__name__)


class SynthesisDataScheduler:
    """Background scheduler for automated data collection."""
    
    def __init__(self):
        self.email_monitor = SynthesisEmailMonitor(
            server=config.email_server,
            port=config.email_port,
            username=config.email_username,
            password=config.email_password,
            use_ssl=config.email_use_ssl
        )
        
        self.db = StudyProgressDB(config.database_path)
        self.running = False
        self.scheduler_thread: Optional[Thread] = None
        
        logger.info("Synthesis Data Scheduler initialized")
    
    def start(self):
        """Start the background scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        
        # Schedule tasks
        schedule.every(5).minutes.do(self._check_emails)
        schedule.every(30).minutes.do(self._update_progress_from_web)
        schedule.every().day.at("08:00").do(self._daily_health_check)
        schedule.every().day.at("20:00").do(self._evening_summary)
        
        # Start scheduler thread
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Background scheduler started")
        
        # Run initial checks
        asyncio.create_task(self._initial_data_collection())
    
    def stop(self):
        """Stop the background scheduler."""
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Background scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler in background thread."""
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    async def _initial_data_collection(self):
        """Run initial data collection on startup."""
        logger.info("Running initial data collection...")
        
        try:
            # Check if we have recent data (within last hour)
            last_session = self.db.get_study_session(datetime.now().strftime("%Y-%m-%d"))
            
            if not last_session or self._is_data_stale(last_session):
                await self._check_emails()
                await self._update_progress_from_web()
            else:
                logger.info("Recent data found, skipping initial collection")
                
        except Exception as e:
            logger.error(f"Error in initial data collection: {e}")
    
    def _is_data_stale(self, session: dict) -> bool:
        """Check if session data is stale (older than 1 hour)."""
        try:
            if not session.get("updated_at"):
                return True
            
            updated_at = datetime.fromisoformat(session["updated_at"])
            age_minutes = (datetime.now() - updated_at).total_seconds() / 60
            
            return age_minutes > 60
            
        except Exception:
            return True
    
    def _check_emails(self):
        """Check for new emails (login codes and progress updates)."""
        try:
            logger.debug("Checking emails for Synthesis updates...")
            
            # Check for login codes
            login_codes = self.email_monitor.get_recent_login_codes(limit=5)
            
            # Check for progress emails
            progress_emails = self.email_monitor.get_progress_emails()
            
            if progress_emails:
                logger.info(f"Found {len(progress_emails)} progress emails")
                for email_data in progress_emails:
                    self._process_progress_email(email_data)
            
            # Check for newsletters (for AI context)
            newsletters = self.email_monitor.get_newsletter_emails()
            if newsletters:
                logger.info(f"Found {len(newsletters)} newsletter emails")
                # Store latest newsletter for AI context
                latest_newsletter = newsletters[0]  # Most recent
                self.db.save_notification(
                    "newsletter",
                    f"📰 New Synthesis newsletter: {latest_newsletter['subject']}"
                )
            
            # Check for payment confirmations
            payments = self.email_monitor.get_payment_emails()
            if payments:
                logger.info(f"Found {len(payments)} payment emails")
                for payment_data in payments:
                    self._process_payment_email(payment_data)
            
            # Clean up old emails
            self.email_monitor.cleanup_old_codes()
            
        except Exception as e:
            logger.error(f"Error checking emails: {e}")
    
    def _process_progress_email(self, email_data: dict):
        """Process a progress email and extract study data."""
        try:
            # Use the parsed data from email monitor
            subject = email_data.get("subject", "")
            study_minutes = email_data.get("study_minutes", 0)
            activities = email_data.get("activities", [])
            achievements = email_data.get("achievements", [])
            student_name = email_data.get("student_name", "")
            
            # Create study data record
            study_data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "logged_in": True,
                "email_processed": True,
                "updated_at": datetime.now().isoformat(),
                "study_minutes": int(study_minutes) if study_minutes else 0,
                "student_name": student_name
            }
            
            # Add activities as lessons completed
            if activities:
                study_data["lessons_completed"] = activities[:5]  # Limit to 5 lessons
            
            # Add achievements if any
            if achievements:
                study_data["achievements"] = achievements
                # Store achievements in notifications for visibility
                for achievement in achievements:
                    self.db.save_notification(
                        "achievement",
                        f"🏆 {student_name} earned: {achievement}"
                    )
            
            # Save to database
            self.db.save_study_session(study_data)
            logger.info(f"Processed progress email for {student_name}: {study_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error processing progress email: {e}")
    
    def _process_payment_email(self, payment_data: dict):
        """Process a payment confirmation email and store billing data."""
        try:
            amount = payment_data.get("amount", 0)
            plan_type = payment_data.get("plan_type", "Unknown")
            
            # Create payment record
            payment_record = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "payment_confirmation",
                "amount": amount,
                "plan_type": plan_type,
                "invoice_url": payment_data.get("invoice_url"),
                "processed_at": datetime.now().isoformat(),
                "subject": payment_data.get("subject", "")
            }
            
            # Save payment notification
            message = f"💳 Payment processed: ${amount} for {plan_type}"
            self.db.save_notification("payment", message)
            
            # Store payment data in a simple way (could be enhanced with separate billing table)
            # For now, save as a special session type
            self.db.save_study_session({
                "date": payment_record["date"],
                "type": "billing",
                "payment_data": payment_record
            })
            
            logger.info(f"Processed payment: ${amount} for {plan_type}")
            
        except Exception as e:
            logger.error(f"Error processing payment email: {e}")
    
    async def _update_progress_from_web(self):
        """Update progress by scraping Synthesis.com dashboard."""
        try:
            logger.debug("Updating progress from web...")
            
            # Only scrape if we don't have recent web data
            today = datetime.now().strftime("%Y-%m-%d")
            session = self.db.get_study_session(today)
            
            if session and session.get("web_scraped") and not self._is_data_stale(session):
                logger.debug("Recent web data exists, skipping scrape")
                return
            
            # Get latest login code
            login_code = self.email_monitor.get_latest_login_code()
            
            if not login_code:
                logger.warning("No login code available for web scraping")
                return
            
            # Scrape data
            async with SynthesisClient(headless=config.headless_browser) as client:
                login_success = await client.login(config.synthesis_email, login_code)
                
                if not login_success:
                    logger.error("Failed to login to Synthesis.com")
                    return
                
                progress_data = await client.get_study_progress()
                
                # Mark as web-scraped data
                progress_data["web_scraped"] = True
                progress_data["updated_at"] = datetime.now().isoformat()
                
                # Merge with existing session data if available
                if session:
                    # Keep email data, add web data
                    progress_data.update({
                        "email_processed": session.get("email_processed", False)
                    })
                
                self.db.save_study_session(progress_data)
                logger.info("Successfully updated progress from web")
                
        except Exception as e:
            logger.error(f"Error updating progress from web: {e}")
    
    def _daily_health_check(self):
        """Daily health check and data validation."""
        try:
            logger.info("Running daily health check...")
            
            # Check database health
            today = datetime.now().strftime("%Y-%m-%d")
            session = self.db.get_study_session(today)
            
            # Check if we have any data for today
            if not session:
                logger.warning("No study session data for today")
                # Trigger immediate data collection
                asyncio.create_task(self._update_progress_from_web())
            
            # Check email connectivity
            try:
                self.email_monitor.test_connection()
                logger.info("Email connection healthy")
            except Exception as e:
                logger.error(f"Email connection issue: {e}")
            
            # Clean up old data (keep last 90 days)
            self.db.cleanup_old_data(days=90)
            
        except Exception as e:
            logger.error(f"Error in daily health check: {e}")
    
    def _evening_summary(self):
        """Generate evening summary and prepare next day."""
        try:
            logger.info("Generating evening summary...")
            
            # Get today's stats
            stats = self.db.get_weekly_stats()
            streak = self.db.get_current_streak()
            
            # Log summary
            logger.info(f"Today's summary - Minutes: {stats.get('total_minutes', 0)}, "
                       f"Streak: {streak} days")
            
            # Save summary notification
            summary_msg = f"Daily Summary: {stats.get('total_minutes', 0)} minutes studied today. "
            if streak > 0:
                summary_msg += f"Current streak: {streak} days! 🔥"
            
            self.db.save_notification("daily_summary", summary_msg)
            
        except Exception as e:
            logger.error(f"Error in evening summary: {e}")
    
    async def trigger_immediate_update(self) -> dict:
        """Trigger immediate data collection (for force_update_progress tool)."""
        try:
            logger.info("Triggering immediate data collection...")
            
            # Run both email and web collection
            await self._check_emails()
            await self._update_progress_from_web()
            
            # Get updated session data
            today = datetime.now().strftime("%Y-%m-%d")
            session = self.db.get_study_session(today)
            
            return {
                "success": True,
                "message": "Data collection completed",
                "session_data": session
            }
            
        except Exception as e:
            logger.error(f"Error in immediate update: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global scheduler instance
_scheduler_instance: Optional[SynthesisDataScheduler] = None


def get_scheduler() -> SynthesisDataScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = SynthesisDataScheduler()
    
    return _scheduler_instance


def start_scheduler():
    """Start the background scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None
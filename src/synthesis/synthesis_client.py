"""
Synthesis.com web automation client for login and progress tracking.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, Page, TimeoutError

logger = logging.getLogger(__name__)


class SynthesisClient:
    """Web automation client for Synthesis.com."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start browser session."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = await self.browser.new_page()
            
            # Set longer timeout for elements
            self.page.set_default_timeout(self.timeout)
            
            logger.info("Browser session started")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def stop(self):
        """Stop browser session."""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Browser session stopped")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
    
    async def login(self, email: str, verification_code: str) -> bool:
        """Login to Synthesis.com using email and verification code."""
        try:
            logger.info("Starting Synthesis login process")
            
            # Navigate to login page
            await self.page.goto("https://synthesis.com/login")
            await self.page.wait_for_load_state("networkidle")
            
            # Enter email
            email_input = await self.page.wait_for_selector('input[type="email"]', timeout=10000)
            await email_input.fill(email)
            
            # Click submit/continue button
            submit_button = await self.page.wait_for_selector('button[type="submit"], button:has-text("Continue")', timeout=5000)
            await submit_button.click()
            
            # Wait for verification code input
            code_input = await self.page.wait_for_selector('input[placeholder*="code"], input[type="text"]', timeout=10000)
            await code_input.fill(verification_code)
            
            # Submit verification code
            verify_button = await self.page.wait_for_selector('button[type="submit"], button:has-text("Verify")', timeout=5000)
            await verify_button.click()
            
            # Wait for successful login (dashboard or main page)
            await self.page.wait_for_load_state("networkidle")
            
            # Check if we're logged in by looking for common dashboard elements
            login_success = await self._check_login_success()
            
            if login_success:
                logger.info("Successfully logged into Synthesis")
                return True
            else:
                logger.error("Login appeared to fail - not on expected page")
                return False
                
        except TimeoutError as e:
            logger.error(f"Timeout during login process: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    
    async def _check_login_success(self) -> bool:
        """Check if login was successful by looking for dashboard elements."""
        try:
            # Look for common elements that indicate successful login
            success_indicators = [
                'text=Dashboard',
                'text=Progress',
                'text=Lessons',
                'text=Study',
                '[data-testid="dashboard"]',
                '.dashboard',
                '#dashboard'
            ]
            
            for indicator in success_indicators:
                try:
                    await self.page.wait_for_selector(indicator, timeout=3000)
                    return True
                except TimeoutError:
                    continue
            
            # Also check URL for dashboard-like patterns
            current_url = self.page.url
            if any(path in current_url for path in ['/dashboard', '/home', '/student', '/portal']):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking login success: {e}")
            return False
    
    async def get_study_progress(self) -> Dict[str, Any]:
        """Extract study progress information from dashboard."""
        try:
            logger.info("Extracting study progress information")
            
            # Navigate to progress/dashboard page if not already there
            current_url = self.page.url
            if 'dashboard' not in current_url and 'progress' not in current_url:
                # Try to find and click dashboard/progress link
                try:
                    dashboard_link = await self.page.wait_for_selector('a:has-text("Dashboard"), a:has-text("Progress")', timeout=5000)
                    await dashboard_link.click()
                    await self.page.wait_for_load_state("networkidle")
                except TimeoutError:
                    logger.warning("Could not find dashboard link, staying on current page")
            
            progress_data = {
                "date": datetime.now().isoformat(),
                "logged_in": True,
                "study_time_minutes": 0,
                "lessons_completed": [],
                "last_activity": None,
                "streak_days": 0,
                "total_points": 0
            }
            
            # Extract study time information
            study_time = await self._extract_study_time()
            if study_time:
                progress_data["study_time_minutes"] = study_time
            
            # Extract completed lessons
            lessons = await self._extract_lessons()
            if lessons:
                progress_data["lessons_completed"] = lessons
            
            # Extract last activity
            last_activity = await self._extract_last_activity()
            if last_activity:
                progress_data["last_activity"] = last_activity
            
            # Extract streak information
            streak = await self._extract_streak()
            if streak:
                progress_data["streak_days"] = streak
            
            # Extract points/score
            points = await self._extract_points()
            if points:
                progress_data["total_points"] = points
            
            logger.info(f"Extracted progress data: {progress_data}")
            return progress_data
            
        except Exception as e:
            logger.error(f"Error extracting study progress: {e}")
            return {"date": datetime.now().isoformat(), "logged_in": True, "error": str(e)}
    
    async def _extract_study_time(self) -> Optional[int]:
        """Extract today's study time in minutes."""
        try:
            # Common selectors for study time
            time_selectors = [
                'text=/\\d+\\s*(minutes?|mins?|hours?)/',
                '[data-testid*="time"]',
                '.study-time',
                '.time-spent',
                '[class*="duration"]'
            ]
            
            for selector in time_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    text = await element.inner_text()
                    
                    # Parse time from text
                    minutes = self._parse_time_to_minutes(text)
                    if minutes is not None:
                        return minutes
                except TimeoutError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting study time: {e}")
            return None
    
    def _parse_time_to_minutes(self, time_text: str) -> Optional[int]:
        """Parse time text into minutes."""
        import re
        
        # Extract numbers and time units
        hours_match = re.search(r'(\\d+)\\s*(?:hours?|hrs?)', time_text, re.IGNORECASE)
        minutes_match = re.search(r'(\\d+)\\s*(?:minutes?|mins?)', time_text, re.IGNORECASE)
        
        total_minutes = 0
        
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        
        return total_minutes if total_minutes > 0 else None
    
    async def _extract_lessons(self) -> List[str]:
        """Extract completed lessons."""
        try:
            lessons = []
            
            # Look for lesson lists or completed items
            lesson_selectors = [
                '.lesson-item',
                '.completed-lesson',
                '[data-testid*="lesson"]',
                '.lesson-title'
            ]
            
            for selector in lesson_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and text.strip():
                            lessons.append(text.strip())
                    
                    if lessons:
                        break
                except Exception:
                    continue
            
            return lessons[:5]  # Return up to 5 recent lessons
            
        except Exception as e:
            logger.error(f"Error extracting lessons: {e}")
            return []
    
    async def _extract_last_activity(self) -> Optional[str]:
        """Extract last activity timestamp."""
        try:
            # Look for "last seen" or activity timestamps
            activity_selectors = [
                'text=/last\\s+(active|seen|login)/',
                '[data-testid*="activity"]',
                '.last-activity',
                '.activity-time'
            ]
            
            for selector in activity_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    text = await element.inner_text()
                    return text.strip()
                except TimeoutError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting last activity: {e}")
            return None
    
    async def _extract_streak(self) -> Optional[int]:
        """Extract streak days."""
        try:
            # Look for streak information
            streak_selectors = [
                'text=/\\d+\\s*day\\s*streak/',
                '[data-testid*="streak"]',
                '.streak',
                '.consecutive-days'
            ]
            
            for selector in streak_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    text = await element.inner_text()
                    
                    # Extract number from streak text
                    import re
                    match = re.search(r'(\\d+)', text)
                    if match:
                        return int(match.group(1))
                except TimeoutError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting streak: {e}")
            return None
    
    async def _extract_points(self) -> Optional[int]:
        """Extract total points or score."""
        try:
            # Look for points/score information
            points_selectors = [
                'text=/\\d+\\s*(points?|pts?)/',
                '[data-testid*="points"]',
                '.points',
                '.score',
                '.total-score'
            ]
            
            for selector in points_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    text = await element.inner_text()
                    
                    # Extract number from points text
                    import re
                    match = re.search(r'(\\d+)', text)
                    if match:
                        return int(match.group(1))
                except TimeoutError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting points: {e}")
            return None
    
    async def take_screenshot(self, path: str = None) -> str:
        """Take a screenshot for debugging."""
        try:
            if not path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = f"synthesis_screenshot_{timestamp}.png"
            
            await self.page.screenshot(path=path, full_page=True)
            logger.info(f"Screenshot saved: {path}")
            return path
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return ""
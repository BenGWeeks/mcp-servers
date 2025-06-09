"""
Configuration for Synthesis Tracker MCP server.
"""

import os
from typing import Optional


class SynthesisConfig:
    """Configuration settings for Synthesis tracker."""
    
    def __init__(self):
        # Email settings for login code monitoring
        self.email_server = os.getenv("EMAIL_SERVER", "imap.gmail.com")
        self.email_port = int(os.getenv("EMAIL_PORT", "993"))
        self.email_username = os.getenv("EMAIL_USERNAME", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.email_use_ssl = os.getenv("EMAIL_USE_SSL", "true").lower() == "true"
        
        # Synthesis.com settings
        self.synthesis_email = os.getenv("SYNTHESIS_EMAIL", "")
        self.synthesis_url = os.getenv("SYNTHESIS_URL", "https://synthesis.com")
        
        # Database settings
        self.database_path = os.getenv("DATABASE_PATH", "./synthesis_data.db")
        
        # Notification settings
        self.notification_enabled = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"
        self.notification_times = os.getenv("NOTIFICATION_TIMES", "09:00,15:00,19:00")
        
        # Browser automation settings
        self.headless_browser = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
        self.browser_timeout = int(os.getenv("BROWSER_TIMEOUT", "30"))
        
        # Study tracking settings
        self.minimum_study_minutes = int(os.getenv("MINIMUM_STUDY_MINUTES", "15"))
        self.study_goal_minutes = int(os.getenv("STUDY_GOAL_MINUTES", "30"))


# Global config instance
config = SynthesisConfig()
"""
Database storage utilities for tracking study progress and user data.
"""

import sqlite3
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class StudyProgressDB:
    """SQLite database for tracking study progress."""
    
    def __init__(self, db_path: str):
        if db_path == ":memory:":
            # For testing, use a temporary file instead of memory
            import tempfile
            self.db_path = tempfile.mktemp(suffix='.db')
            self._is_temp = True
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._is_temp = False
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Main study tracking table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS study_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        logged_in BOOLEAN NOT NULL DEFAULT 0,
                        login_time TEXT,
                        study_minutes INTEGER DEFAULT 0,
                        lessons_completed TEXT,  -- JSON array
                        last_activity TEXT,
                        streak_days INTEGER DEFAULT 0,
                        total_points INTEGER DEFAULT 0,
                        raw_data TEXT,  -- JSON of all extracted data
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create unique index on date
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_study_sessions_date 
                    ON study_sessions(date)
                """)
                
                # Notification tracking table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        notification_type TEXT NOT NULL,  -- 'reminder', 'achievement', 'streak'
                        message TEXT NOT NULL,
                        sent_at TEXT NOT NULL,
                        response TEXT  -- User response if any
                    )
                """)
                
                # User goals and settings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                logger.info(f"Database initialized: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_study_session(self, progress_data: Dict[str, Any]) -> bool:
        """Save or update study session data."""
        try:
            date = progress_data.get("date", datetime.now().isoformat())[:10]  # YYYY-MM-DD
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Convert lessons list to JSON
                lessons_json = json.dumps(progress_data.get("lessons_completed", []))
                raw_data_json = json.dumps(progress_data)
                
                now = datetime.now().isoformat()
                
                # Insert or update session data
                cursor.execute("""
                    INSERT OR REPLACE INTO study_sessions 
                    (date, logged_in, login_time, study_minutes, lessons_completed, 
                     last_activity, streak_days, total_points, raw_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            COALESCE((SELECT created_at FROM study_sessions WHERE date = ?), ?), ?)
                """, (
                    date,
                    progress_data.get("logged_in", False),
                    progress_data.get("login_time"),
                    progress_data.get("study_time_minutes", 0),
                    lessons_json,
                    progress_data.get("last_activity"),
                    progress_data.get("streak_days", 0),
                    progress_data.get("total_points", 0),
                    raw_data_json,
                    date, now, now
                ))
                
                conn.commit()
                logger.info(f"Saved study session for {date}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving study session: {e}")
            return False
    
    def get_study_session(self, date: str = None) -> Optional[Dict[str, Any]]:
        """Get study session data for a specific date."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM study_sessions WHERE date = ?
                """, (date,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    session_data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    if session_data.get("lessons_completed"):
                        session_data["lessons_completed"] = json.loads(session_data["lessons_completed"])
                    if session_data.get("raw_data"):
                        session_data["raw_data"] = json.loads(session_data["raw_data"])
                    
                    return session_data
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting study session for {date}: {e}")
            return None
    
    def get_recent_sessions(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get study sessions for the last N days."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM study_sessions 
                    WHERE date >= ? 
                    ORDER BY date DESC
                """, (start_date,))
                
                sessions = []
                columns = [desc[0] for desc in cursor.description]
                
                for row in cursor.fetchall():
                    session_data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    if session_data.get("lessons_completed"):
                        session_data["lessons_completed"] = json.loads(session_data["lessons_completed"])
                    if session_data.get("raw_data"):
                        session_data["raw_data"] = json.loads(session_data["raw_data"])
                    
                    sessions.append(session_data)
                
                return sessions
                
        except Exception as e:
            logger.error(f"Error getting recent sessions: {e}")
            return []
    
    def get_weekly_stats(self) -> Dict[str, Any]:
        """Get weekly study statistics."""
        try:
            week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get basic stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as days_logged_in,
                        SUM(study_minutes) as total_minutes,
                        AVG(study_minutes) as avg_minutes,
                        MAX(streak_days) as max_streak,
                        SUM(total_points) as total_points
                    FROM study_sessions 
                    WHERE date >= ? AND logged_in = 1
                """, (week_start,))
                
                stats = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
                
                # Get daily breakdown
                cursor.execute("""
                    SELECT date, study_minutes, logged_in 
                    FROM study_sessions 
                    WHERE date >= ? 
                    ORDER BY date DESC
                """, (week_start,))
                
                daily_data = []
                for row in cursor.fetchall():
                    daily_data.append({
                        "date": row[0],
                        "study_minutes": row[1],
                        "logged_in": bool(row[2])
                    })
                
                stats["daily_breakdown"] = daily_data
                stats["week_start"] = week_start
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting weekly stats: {e}")
            return {}
    
    def save_notification(self, notification_type: str, message: str, date: str = None) -> bool:
        """Save notification record."""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO notifications (date, notification_type, message, sent_at)
                    VALUES (?, ?, ?, ?)
                """, (date, notification_type, message, datetime.now().isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving notification: {e}")
            return False
    
    def get_todays_notifications(self) -> List[Dict[str, Any]]:
        """Get notifications sent today."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM notifications 
                    WHERE date = ? 
                    ORDER BY sent_at DESC
                """, (today,))
                
                notifications = []
                columns = [desc[0] for desc in cursor.description]
                
                for row in cursor.fetchall():
                    notifications.append(dict(zip(columns, row)))
                
                return notifications
                
        except Exception as e:
            logger.error(f"Error getting today's notifications: {e}")
            return []
    
    def set_user_setting(self, key: str, value: str) -> bool:
        """Set user setting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO user_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (key, value, datetime.now().isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting user setting {key}: {e}")
            return False
    
    def get_user_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get user setting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT value FROM user_settings WHERE key = ?
                """, (key,))
                
                row = cursor.fetchone()
                return row[0] if row else default
                
        except Exception as e:
            logger.error(f"Error getting user setting {key}: {e}")
            return default
    
    def has_studied_today(self) -> bool:
        """Check if user has studied today."""
        today = datetime.now().strftime("%Y-%m-%d")
        session = self.get_study_session(today)
        
        if not session:
            return False
        
        return session.get("logged_in", False) and session.get("study_minutes", 0) > 0
    
    def get_current_streak(self) -> int:
        """Calculate current study streak."""
        try:
            # Get recent sessions to calculate streak
            sessions = self.get_recent_sessions(30)  # Look back 30 days
            
            if not sessions:
                return 0
            
            # Sort by date (newest first)
            sessions.sort(key=lambda x: x["date"], reverse=True)
            
            streak = 0
            for session in sessions:
                if session.get("logged_in") and session.get("study_minutes", 0) > 0:
                    streak += 1
                else:
                    break  # Streak broken
            
            return streak
            
        except Exception as e:
            logger.error(f"Error calculating streak: {e}")
            return 0
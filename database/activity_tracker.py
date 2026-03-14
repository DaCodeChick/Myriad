"""
Activity Tracker - User activity pattern analysis for Circadian Rhythm Engine.

This module tracks user message activity and calculates activity probability
based on historical patterns for the Spontaneous Autonomy system.

Part of Project Myriad's Spontaneous Autonomy feature.
"""

import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ActivityTracker:
    """Tracks user activity patterns and calculates circadian rhythm probabilities."""

    def __init__(self, db_path: str = "data/activity_logs.db"):
        """
        Initialize the activity tracker.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Create the user_activity_logs and last_channels tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )

        # Create indices for fast lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activity_user 
            ON user_activity_logs(user_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp 
            ON user_activity_logs(timestamp)
        """
        )

        # Create table for tracking last channel per user (for spontaneous outreach)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS last_channels (
                user_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

    def log_activity(self, user_id: str, persona_id: str) -> None:
        """
        Log a user activity event (message sent).

        Args:
            user_id: User identifier
            persona_id: Active persona identifier
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()

        cursor.execute(
            """
            INSERT INTO user_activity_logs (user_id, persona_id, timestamp)
            VALUES (?, ?, ?)
        """,
            (user_id, persona_id, timestamp),
        )

        conn.commit()
        conn.close()

    def get_last_activity(self, user_id: str, persona_id: str) -> Optional[datetime]:
        """
        Get the timestamp of the user's last activity with a specific persona.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            datetime of last activity, or None if no activity found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT timestamp FROM user_activity_logs
            WHERE user_id = ? AND persona_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (user_id, persona_id),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return datetime.fromisoformat(row[0])
        return None

    def get_activity_probability(self, user_id: str, current_hour: int) -> float:
        """
        Calculate activity probability for a given hour based on last 7 days of history.

        Analyzes user's historical activity patterns to determine likelihood
        of being active/awake during a specific hour.

        Args:
            user_id: User identifier
            current_hour: Hour of day (0-23)

        Returns:
            Probability from 0.0 (asleep/inactive) to 1.0 (highly active)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get activity from last 7 days
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        cursor.execute(
            """
            SELECT timestamp FROM user_activity_logs
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """,
            (user_id, seven_days_ago),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            # No data - assume moderate probability (neutral stance)
            return 0.5

        # Count messages per hour
        hour_counts = defaultdict(int)
        total_messages = 0

        for row in rows:
            timestamp = datetime.fromisoformat(row[0])
            hour = timestamp.hour
            hour_counts[hour] += 1
            total_messages += 1

        # Calculate probability for the requested hour
        # Use a sliding window: count messages in current_hour ± 1 hour
        window_count = 0
        for offset in [-1, 0, 1]:
            window_hour = (current_hour + offset) % 24
            window_count += hour_counts[window_hour]

        # Normalize by total messages and window size
        if total_messages == 0:
            return 0.5

        # Base probability from raw frequency
        raw_probability = window_count / total_messages

        # Scale up by multiplying by number of days with data (up to 7)
        # This prevents low scores just because user hasn't talked much
        days_with_data = min(
            len(set(datetime.fromisoformat(row[0]).date() for row in rows)), 7
        )
        scaling_factor = days_with_data / 7.0

        # Calculate final probability with scaling
        # Multiply by 3 to amplify signal (since we're looking at ±1 hour window)
        probability = min(raw_probability * 3 * (0.5 + 0.5 * scaling_factor), 1.0)

        return probability

    def get_hours_since_last_activity(
        self, user_id: str, persona_id: str
    ) -> Optional[float]:
        """
        Get hours since user's last activity with a persona.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Hours since last activity, or None if no activity found
        """
        last_activity = self.get_last_activity(user_id, persona_id)
        if last_activity:
            delta = datetime.utcnow() - last_activity
            return delta.total_seconds() / 3600.0
        return None

    def get_activity_stats(self, user_id: str, days: int = 7) -> Dict[str, any]:
        """
        Get activity statistics for a user.

        Args:
            user_id: User identifier
            days: Number of days to analyze (default: 7)

        Returns:
            Dictionary with activity statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        cursor.execute(
            """
            SELECT timestamp FROM user_activity_logs
            WHERE user_id = ? AND timestamp >= ?
        """,
            (user_id, cutoff),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"total_messages": 0, "active_hours": [], "peak_hour": None}

        hour_counts = defaultdict(int)
        for row in rows:
            timestamp = datetime.fromisoformat(row[0])
            hour_counts[timestamp.hour] += 1

        peak_hour = (
            max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
        )

        return {
            "total_messages": len(rows),
            "active_hours": sorted(hour_counts.keys()),
            "peak_hour": peak_hour,
            "hour_distribution": dict(hour_counts),
        }

    def update_last_channel(self, user_id: str, channel_id: str) -> None:
        """
        Update the last channel a user was active in.

        This is used by the autonomy daemon to know where to send spontaneous messages.

        Args:
            user_id: User identifier
            channel_id: Channel identifier
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO last_channels (user_id, channel_id, updated_at)
            VALUES (?, ?, ?)
        """,
            (user_id, channel_id, timestamp),
        )

        conn.commit()
        conn.close()

    def get_last_channel(self, user_id: str) -> Optional[str]:
        """
        Get the last channel a user was active in.

        Args:
            user_id: User identifier

        Returns:
            Channel ID as string, or None if no channel found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT channel_id FROM last_channels
            WHERE user_id = ?
        """,
            (user_id,),
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def clear_old_logs(self, days_to_keep: int = 30) -> None:
        """
        Clear activity logs older than specified days.

        Args:
            days_to_keep: Number of days of logs to retain (default: 30)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days_to_keep)).isoformat()

        cursor.execute(
            """
            DELETE FROM user_activity_logs
            WHERE timestamp < ?
        """,
            (cutoff,),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count

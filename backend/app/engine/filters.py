"""
Session and timing filters for the SignalPipeline.

Determines whether trading is allowed based on:
  - Day of week (block weekends)
  - Active trading sessions (London, New York)
"""

from datetime import datetime


class SessionFilter:
    """
    Filters signals based on trading session hours.

    Active sessions (UTC):
      - London:  08:00 - 16:00
      - New York: 13:00 - 21:00
      - Overlap:  13:00 - 16:00 (highest liquidity)

    Blocked:
      - Saturday and Sunday (weekend)
      - Hours outside all active sessions
    """

    # Session definitions as (start_hour, end_hour) in UTC
    SESSIONS = {
        "london": (8, 16),
        "new_york": (13, 21),
    }

    def is_active_session(self, timestamp: datetime) -> bool:
        """
        Check if timestamp falls in an active trading session.

        Args:
            timestamp: Datetime to check (should be UTC-aware or naive UTC).

        Returns:
            True if the timestamp is within an active session on a weekday.
        """
        # Block weekends: Saturday = 5, Sunday = 6
        if timestamp.weekday() >= 5:
            return False

        hour = timestamp.hour

        # Check if the hour falls within any active session
        for session_name, (start, end) in self.SESSIONS.items():
            if start <= hour < end:
                return True

        return False

    def get_active_sessions(self, timestamp: datetime) -> list[str]:
        """
        Return list of currently active session names.

        Args:
            timestamp: Datetime to check.

        Returns:
            List of active session names (e.g., ["london", "new_york"]).
        """
        if timestamp.weekday() >= 5:
            return []

        hour = timestamp.hour
        active = []

        for session_name, (start, end) in self.SESSIONS.items():
            if start <= hour < end:
                active.append(session_name)

        return active

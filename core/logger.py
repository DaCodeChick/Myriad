"""
Centralized logging utility for Project Myriad.

Provides timestamped, persona-tagged console output for:
- Brain (text LLM) messages
- Eyes (vision) processing
- Thoughts (metacognition)
"""

from datetime import datetime
from typing import Optional


class MyriadLogger:
    """Centralized logger with timestamp and persona formatting."""

    # ANSI color codes
    COLOR_RESET = "\033[0m"
    COLOR_USER = "\033[94m"  # Blue
    COLOR_AI = "\033[92m"  # Green
    COLOR_THOUGHT = "\033[93m"  # Yellow
    COLOR_VISION = "\033[95m"  # Magenta
    COLOR_TIMESTAMP = "\033[90m"  # Dark gray

    def __init__(
        self, brain_logging_enabled: bool = False, eyes_logging_enabled: bool = False
    ):
        """
        Initialize logger with configuration flags.

        Args:
            brain_logging_enabled: Enable logging for LLM (text) operations
            eyes_logging_enabled: Enable logging for vision operations
        """
        self.brain_logging_enabled = brain_logging_enabled
        self.eyes_logging_enabled = eyes_logging_enabled

    @staticmethod
    def _format_timestamp() -> str:
        """Format current time as 12-hour clock with seconds."""
        now = datetime.now()
        return now.strftime("%I:%M:%S %p")

    def log_user_message(self, user_name: str, message: str) -> None:
        """Log a user message."""
        if not self.brain_logging_enabled:
            return

        timestamp = self._format_timestamp()
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_USER}[{user_name}]:{self.COLOR_RESET} {message}"
        )

    def log_ai_message(self, persona_name: str, message: str) -> None:
        """Log an AI response message."""
        if not self.brain_logging_enabled:
            return

        timestamp = self._format_timestamp()
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_AI}[{persona_name}]:{self.COLOR_RESET} {message}"
        )

    def log_thought(self, persona_name: str, thought: str) -> None:
        """Log a metacognition thought."""
        if not self.brain_logging_enabled:
            return

        timestamp = self._format_timestamp()
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_THOUGHT}{persona_name} thinks about {thought}{self.COLOR_RESET}"
        )

    def log_vision(self, persona_name: str, description: str) -> None:
        """Log a vision/appearance description."""
        if not self.eyes_logging_enabled:
            return

        timestamp = self._format_timestamp()
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_VISION}{persona_name} is {description}{self.COLOR_RESET}"
        )

    def log_brain_request(self, persona_name: str, message_count: int) -> None:
        """Log an outgoing LLM API request."""
        if not self.brain_logging_enabled:
            return

        timestamp = self._format_timestamp()
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_AI}[Brain Request - {persona_name}]:{self.COLOR_RESET} Processing {message_count} messages..."
        )

    def log_brain_response(self, persona_name: str, response_preview: str) -> None:
        """Log an incoming LLM API response."""
        if not self.brain_logging_enabled:
            return

        timestamp = self._format_timestamp()
        # Truncate preview to 100 chars
        preview = (
            response_preview[:100] + "..."
            if len(response_preview) > 100
            else response_preview
        )
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_AI}[Brain Response - {persona_name}]:{self.COLOR_RESET} {preview}"
        )

    def log_vision_request(self, persona_name: str, image_description: str) -> None:
        """Log an outgoing vision API request."""
        if not self.eyes_logging_enabled:
            return

        timestamp = self._format_timestamp()
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_VISION}[Eyes Request - {persona_name}]:{self.COLOR_RESET} Processing {image_description}..."
        )

    def log_vision_response(self, persona_name: str, description_preview: str) -> None:
        """Log an incoming vision API response."""
        if not self.eyes_logging_enabled:
            return

        timestamp = self._format_timestamp()
        # Truncate preview to 100 chars
        preview = (
            description_preview[:100] + "..."
            if len(description_preview) > 100
            else description_preview
        )
        print(
            f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_VISION}[Eyes Response - {persona_name}]:{self.COLOR_RESET} {preview}"
        )


# Global logger instance (will be initialized with config)
_global_logger: Optional[MyriadLogger] = None


def initialize_logger(
    brain_logging_enabled: bool = False, eyes_logging_enabled: bool = False
) -> None:
    """Initialize the global logger instance."""
    global _global_logger
    _global_logger = MyriadLogger(brain_logging_enabled, eyes_logging_enabled)


def get_logger() -> MyriadLogger:
    """Get the global logger instance."""
    global _global_logger
    if _global_logger is None:
        # Default to disabled logging if not initialized
        _global_logger = MyriadLogger(False, False)
    return _global_logger

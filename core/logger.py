"""
Centralized logging utility for Project Myriad.

Provides timestamped, persona-tagged output for:
- Brain (text LLM) messages
- Eyes (vision) processing
- Thoughts (metacognition)

Supports both console and file logging independently.
"""

import os
from datetime import datetime
from pathlib import Path
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
        self,
        brain_console_enabled: bool = False,
        eyes_console_enabled: bool = False,
        brain_file_enabled: bool = False,
        eyes_file_enabled: bool = False,
        log_dir: str = "logs",
    ):
        """
        Initialize logger with configuration flags.

        Args:
            brain_console_enabled: Enable console logging for LLM (text) operations
            eyes_console_enabled: Enable console logging for vision operations
            brain_file_enabled: Enable file logging for LLM operations
            eyes_file_enabled: Enable file logging for vision operations
            log_dir: Directory for log files (default: "logs")
        """
        self.brain_console_enabled = brain_console_enabled
        self.eyes_console_enabled = eyes_console_enabled
        self.brain_file_enabled = brain_file_enabled
        self.eyes_file_enabled = eyes_file_enabled
        self.log_dir = log_dir

        # Create log directory if file logging is enabled
        if brain_file_enabled or eyes_file_enabled:
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # Generate log file names with date
            date_str = datetime.now().strftime("%Y-%m-%d")
            self.brain_log_file = os.path.join(log_dir, f"brain_{date_str}.log")
            self.eyes_log_file = os.path.join(log_dir, f"eyes_{date_str}.log")

    @staticmethod
    def _format_timestamp() -> str:
        """Format current time as 12-hour clock with seconds."""
        now = datetime.now()
        return now.strftime("%I:%M:%S %p")

    @staticmethod
    def _format_timestamp_file() -> str:
        """Format timestamp for file logging (24-hour with date)."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def _write_to_file(self, filepath: str, message: str) -> None:
        """Write a message to a log file."""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception as e:
            print(f"Warning: Failed to write to log file {filepath}: {e}")

    def log_user_message(self, user_name: str, message: str) -> None:
        """Log a user message."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Console output
        if self.brain_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_USER}[{user_name}]:{self.COLOR_RESET} {message}"
            )

        # File output
        if self.brain_file_enabled:
            log_msg = f"[{timestamp_file}] [USER: {user_name}] {message}"
            self._write_to_file(self.brain_log_file, log_msg)

    def log_ai_message(self, persona_name: str, message: str) -> None:
        """Log an AI response message."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Console output
        if self.brain_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_AI}[{persona_name}]:{self.COLOR_RESET} {message}"
            )

        # File output
        if self.brain_file_enabled:
            log_msg = f"[{timestamp_file}] [AI: {persona_name}] {message}"
            self._write_to_file(self.brain_log_file, log_msg)

    def log_thought(self, persona_name: str, thought: str) -> None:
        """Log a metacognition thought."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Console output - narrative format
        if self.brain_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_THOUGHT}{persona_name} is thinking... {thought}{self.COLOR_RESET}"
            )

        # File output
        if self.brain_file_enabled:
            log_msg = f"[{timestamp_file}] [THOUGHT: {persona_name}] {thought}"
            self._write_to_file(self.brain_log_file, log_msg)

    def log_vision(self, persona_name: str, description: str) -> None:
        """Log a vision/appearance description."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Console output
        if self.eyes_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_VISION}{persona_name} is {description}{self.COLOR_RESET}"
            )

        # File output
        if self.eyes_file_enabled:
            log_msg = f"[{timestamp_file}] [VISION: {persona_name}] {description}"
            self._write_to_file(self.eyes_log_file, log_msg)

    def log_brain_request(self, persona_name: str, message_count: int) -> None:
        """Log an outgoing LLM API request."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Console output
        if self.brain_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_AI}[Brain Request - {persona_name}]:{self.COLOR_RESET} Processing {message_count} messages..."
            )

        # File output
        if self.brain_file_enabled:
            log_msg = f"[{timestamp_file}] [BRAIN REQUEST: {persona_name}] Processing {message_count} messages"
            self._write_to_file(self.brain_log_file, log_msg)

    def log_brain_response(self, persona_name: str, response_preview: str) -> None:
        """Log an incoming LLM API response."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Truncate preview to 100 chars for console
        preview = (
            response_preview[:100] + "..."
            if len(response_preview) > 100
            else response_preview
        )

        # Console output
        if self.brain_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_AI}[{persona_name}]:{self.COLOR_RESET} {preview}"
            )

        # File output (full response, not truncated)
        if self.brain_file_enabled:
            log_msg = f"[{timestamp_file}] [BRAIN RESPONSE: {persona_name}] {response_preview}"
            self._write_to_file(self.brain_log_file, log_msg)

    def log_vision_request(self, persona_name: str, image_description: str) -> None:
        """Log an outgoing vision API request."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Console output
        if self.eyes_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_VISION}[Eyes Request - {persona_name}]:{self.COLOR_RESET} Processing {image_description}..."
            )

        # File output
        if self.eyes_file_enabled:
            log_msg = (
                f"[{timestamp_file}] [EYES REQUEST: {persona_name}] {image_description}"
            )
            self._write_to_file(self.eyes_log_file, log_msg)

    def log_vision_response(self, persona_name: str, description_preview: str) -> None:
        """Log an incoming vision API response."""
        timestamp = self._format_timestamp()
        timestamp_file = self._format_timestamp_file()

        # Truncate preview to 100 chars for console
        preview = (
            description_preview[:100] + "..."
            if len(description_preview) > 100
            else description_preview
        )

        # Console output
        if self.eyes_console_enabled:
            print(
                f"{self.COLOR_TIMESTAMP}[{timestamp}]{self.COLOR_RESET} {self.COLOR_VISION}[Eyes Response - {persona_name}]:{self.COLOR_RESET} {preview}"
            )

        # File output (full description, not truncated)
        if self.eyes_file_enabled:
            log_msg = f"[{timestamp_file}] [EYES RESPONSE: {persona_name}] {description_preview}"
            self._write_to_file(self.eyes_log_file, log_msg)


# Global logger instance (will be initialized with config)
_global_logger: Optional[MyriadLogger] = None


def initialize_logger(
    brain_console_enabled: bool = False,
    eyes_console_enabled: bool = False,
    brain_file_enabled: bool = False,
    eyes_file_enabled: bool = False,
    log_dir: str = "logs",
) -> None:
    """Initialize the global logger instance."""
    global _global_logger
    _global_logger = MyriadLogger(
        brain_console_enabled=brain_console_enabled,
        eyes_console_enabled=eyes_console_enabled,
        brain_file_enabled=brain_file_enabled,
        eyes_file_enabled=eyes_file_enabled,
        log_dir=log_dir,
    )


def get_logger() -> MyriadLogger:
    """Get the global logger instance."""
    global _global_logger
    if _global_logger is None:
        # Default to disabled logging if not initialized
        _global_logger = MyriadLogger(False, False, False, False)
    return _global_logger

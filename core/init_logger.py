"""
Initialization logger for Project Myriad.

Provides simple logging for initialization/startup messages with configurable log levels.
Separate from the main application logger (which handles brain/eyes logging).
"""

from enum import IntEnum
from typing import Optional


class InitLogLevel(IntEnum):
    """Log levels for initialization logging."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


class InitLogger:
    """Simple logger for initialization messages."""

    _current_level: InitLogLevel = InitLogLevel.INFO

    @classmethod
    def set_level(cls, level: str) -> None:
        """
        Set the log level from string.

        Args:
            level: One of "DEBUG", "INFO", "WARNING", "ERROR"
        """
        level_map = {
            "DEBUG": InitLogLevel.DEBUG,
            "INFO": InitLogLevel.INFO,
            "WARNING": InitLogLevel.WARNING,
            "ERROR": InitLogLevel.ERROR,
        }
        cls._current_level = level_map.get(level.upper(), InitLogLevel.INFO)

    @classmethod
    def debug(cls, message: str) -> None:
        """Log debug message (verbose initialization tracking)."""
        if cls._current_level <= InitLogLevel.DEBUG:
            print(message, flush=True)

    @classmethod
    def info(cls, message: str) -> None:
        """Log info message (normal initialization messages)."""
        if cls._current_level <= InitLogLevel.INFO:
            print(message, flush=True)

    @classmethod
    def warning(cls, message: str) -> None:
        """Log warning message."""
        if cls._current_level <= InitLogLevel.WARNING:
            print(message, flush=True)

    @classmethod
    def error(cls, message: str) -> None:
        """Log error message."""
        if cls._current_level <= InitLogLevel.ERROR:
            print(message, flush=True)


# Convenience alias
init_log = InitLogger

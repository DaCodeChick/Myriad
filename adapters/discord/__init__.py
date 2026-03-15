"""
Discord adapter module for Project Myriad.

Provides Discord-specific bot implementation and utilities.
"""

from adapters.discord.bot import MyriadDiscordBot, create_discord_bot
from adapters.discord.utils import chunk_message

__all__ = ["MyriadDiscordBot", "create_discord_bot", "chunk_message"]

"""
Base command utilities for Discord commands.

Provides common decorators and helpers for command handlers.
"""

import discord
from typing import Optional
from core.agent_core import AgentCore


async def require_active_persona(
    interaction: discord.Interaction, agent_core: AgentCore
) -> Optional[str]:
    """
    Check if user has an active persona.

    Args:
        interaction: Discord interaction
        agent_core: Agent core instance

    Returns:
        User ID if persona exists, None otherwise (with error message sent)
    """
    user_id = str(interaction.user.id)
    persona = agent_core.get_active_persona(user_id)

    if not persona:
        available = agent_core.list_personas()
        await interaction.response.send_message(
            f"You don't have an active persona.\n"
            f"Use `/swap <persona_id>` to select one.\n\n"
            f"Available personas: {', '.join(available)}",
            ephemeral=True,
        )
        return None

    return user_id


class ResponseFormatter:
    """Consistent formatting for command responses."""

    @staticmethod
    def success(message: str) -> str:
        """Format success message."""
        return f"✓ {message}"

    @staticmethod
    def error(message: str) -> str:
        """Format error message."""
        return f"✗ {message}"

    @staticmethod
    def warning(message: str) -> str:
        """Format warning message."""
        return f"⚠️ {message}"

    @staticmethod
    def info(message: str) -> str:
        """Format info message."""
        return f"ℹ {message}"

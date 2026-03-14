"""
Mode override commands for Discord.

Handles dynamic behavioral mode switching (OOC, HENTAI, NORMAL).
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING, Literal

from adapters.commands.base import ResponseFormatter
from database.mode_manager import BehaviorMode

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_mode_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all mode-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="mode", description="Switch behavioral mode (normal, ooc, hentai)"
    )
    @app_commands.describe(
        mode="The behavioral mode to activate (normal, ooc, or hentai)"
    )
    async def mode_switch(
        interaction: discord.Interaction,
        mode: Literal["normal", "ooc", "hentai"],
    ):
        """
        Switch the user's active behavioral mode.

        Modes:
        - normal: Standard persona behavior
        - ooc: Out of Character - meta-RP management with global memory access
        - hentai: Adult content override (future implementation)
        """
        user_id = str(interaction.user.id)

        # Convert string to BehaviorMode enum
        mode_enum = BehaviorMode(mode.lower())

        # Set the mode
        success = bot.agent_core.mode_manager.set_active_mode(user_id, mode_enum)

        if success:
            # Build mode-specific response
            if mode_enum == BehaviorMode.OOC:
                response = (
                    "🔧 **OOC Mode Activated**\n\n"
                    "You are now in Out of Character mode. The AI will:\n"
                    "• Bypass persona behavior and act as a helpful assistant\n"
                    "• Disable Limbic System, Cadence Degrader, and Metacognition\n"
                    "• Access ALL memories across all personas and timelines\n"
                    "• Help you manage RP sessions, timelines, and character development\n\n"
                    "Use `/mode normal` to return to standard roleplay mode."
                )
            elif mode_enum == BehaviorMode.HENTAI:
                response = (
                    "🔞 **HENTAI Mode Activated**\n\n"
                    "Adult content filtering override enabled.\n"
                    "(Future implementation - currently behaves as NORMAL mode)\n\n"
                    "Use `/mode normal` to return to standard mode."
                )
            else:  # NORMAL
                response = (
                    "✅ **Normal Mode Restored**\n\n"
                    "Standard persona behavior resumed:\n"
                    "• Persona system prompt active\n"
                    "• Limbic System enabled\n"
                    "• Cadence Degrader enabled\n"
                    "• Metacognition enabled\n"
                    "• Memory scoped to current persona/timeline"
                )

            await interaction.response.send_message(
                response,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Failed to set mode to '{mode}'. Please try again."
                ),
                ephemeral=True,
            )

    @bot.tree.command(
        name="mode_status", description="Check your current behavioral mode"
    )
    async def mode_status(interaction: discord.Interaction):
        """Show the user's current active behavioral mode."""
        user_id = str(interaction.user.id)
        active_mode = bot.agent_core.mode_manager.get_active_mode(user_id)
        mode_override = bot.agent_core.mode_manager.get_mode_override(user_id)

        # Build status message
        status_emoji = {
            BehaviorMode.NORMAL: "✅",
            BehaviorMode.OOC: "🔧",
            BehaviorMode.HENTAI: "🔞",
        }

        response = f"{status_emoji[active_mode]} **Current Mode: {active_mode.value.upper()}**\n\n"

        # Show active overrides
        if active_mode != BehaviorMode.NORMAL:
            response += "**Active Overrides:**\n"
            if mode_override.bypass_persona:
                response += "• Persona bypassed (using Assistant prompt)\n"
            if mode_override.disable_limbic:
                response += "• Limbic System disabled\n"
            if mode_override.disable_cadence:
                response += "• Cadence Degrader disabled\n"
            if mode_override.disable_autonomy:
                response += "• Spontaneous Autonomy disabled\n"
            if mode_override.disable_metacognition:
                response += "• Metacognition disabled\n"
            if mode_override.global_memory_access:
                response += "• Global Memory Access enabled (all personas/lives)\n"
        else:
            response += "No overrides active. Standard persona behavior."

        response += "\n\nUse `/mode <normal|ooc|hentai>` to switch modes."

        await interaction.response.send_message(
            response,
            ephemeral=True,
        )

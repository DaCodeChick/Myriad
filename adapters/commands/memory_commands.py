"""
Memory management commands for Discord.

Handles memory clearing and statistics.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING, Optional

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_memory_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all memory-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(name="forget", description="Clear your conversation memory")
    @app_commands.describe(
        persona_id="Optional: Clear only memories from this persona. Leave blank to clear ALL."
    )
    async def forget(
        interaction: discord.Interaction, persona_id: Optional[str] = None
    ):
        """Clear conversation memory for the user."""
        user_id = str(interaction.user.id)

        # Clear memories
        bot.agent_core.clear_user_memory(user_id, persona_id)

        if persona_id:
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Cleared all memories from persona `{persona_id}`."
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.success("Cleared ALL conversation memories."),
                ephemeral=True,
            )

    @bot.tree.command(name="stats", description="View your memory statistics")
    async def stats(interaction: discord.Interaction):
        """Show memory statistics for the user."""
        user_id = str(interaction.user.id)
        stats = bot.agent_core.get_memory_stats(user_id)

        await interaction.response.send_message(
            f"**Memory Statistics:**\n"
            f"• Total Memories: {stats['total_memories']}\n"
            f"• Global (Shared): {stats['global_memories']}\n"
            f"• Isolated (Persona-specific): {stats['isolated_memories']}\n"
            f"• Active Persona: `{stats['active_persona'] or 'None'}`",
            ephemeral=True,
        )

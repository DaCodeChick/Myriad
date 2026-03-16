"""
Session Note Commands - Silent meta-level context injection.

Provides /note command for injecting silent directives into the prompt context
without generating a public response (unlike /dm which acts as an active narrator).

Part of Project Myriad's meta-control toolkit.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING, Optional

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_note_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register session note commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="note", description="Set a silent meta-note to inject into AI context"
    )
    @app_commands.describe(
        text="The note to inject into context (use 'clear' to remove the note)"
    )
    async def set_note(interaction: discord.Interaction, text: str):
        """Set or clear a silent session note."""
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer
            return

        user_id = str(interaction.user.id)

        # Check if user wants to clear the note
        if text.lower().strip() in ["clear", "remove", "delete", ""]:
            cleared = bot.agent_core.session_notes.clear_note(user_id)

            if cleared:
                await interaction.followup.send(
                    ResponseFormatter.success("📝 Session note cleared."),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    ResponseFormatter.warning("No active session note to clear."),
                    ephemeral=True,
                )
            return

        # Set the note
        bot.agent_core.session_notes.set_note(user_id, text)

        # Show confirmation with preview
        preview = text[:100] + "..." if len(text) > 100 else text

        await interaction.followup.send(
            ResponseFormatter.success(
                f"📝 **Session Note Set**\n\n"
                f"This note will be silently injected into the AI's context:\n"
                f"```\n{preview}\n```\n"
                f"Use `/note clear` to remove it."
            ),
            ephemeral=True,
        )

    @bot.tree.command(
        name="note_status", description="Check if you have an active session note"
    )
    async def note_status(interaction: discord.Interaction):
        """Show the current session note status."""
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer
            return

        user_id = str(interaction.user.id)

        note_text = bot.agent_core.session_notes.get_note(user_id)

        if note_text:
            # Show the active note
            preview = note_text[:200] + "..." if len(note_text) > 200 else note_text

            await interaction.followup.send(
                f"📝 **Active Session Note:**\n```\n{preview}\n```\n"
                f"Character count: {len(note_text)}\n\n"
                f"This note is being silently injected into every AI response.\n"
                f"Use `/note clear` to remove it.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                ResponseFormatter.info(
                    "No active session note.\n\n"
                    'Use `/note text="your note here"` to set one.'
                ),
                ephemeral=True,
            )

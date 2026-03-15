"""
Configuration commands - persona settings like narrator mode.

Handles persona configuration and behavioral settings.

Part of RDSSC Phase 1 refactoring - split from persona_commands.py.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_config_commands(
    persona_group: app_commands.Group, bot: "MyriadDiscordBot"
) -> None:
    """
    Register persona configuration commands (set_narrator, etc.).

    Args:
        persona_group: The persona command group to add commands to
        bot: The Discord bot instance
    """

    @persona_group.command(
        name="set_narrator",
        description="Mark a persona as a Narrator/DM (no physical body, controls environment)",
    )
    @app_commands.describe(
        persona_id="The ID of the persona to mark as narrator",
        is_narrator="True to enable narrator mode, False to disable",
    )
    async def set_narrator(
        interaction: discord.Interaction, persona_id: str, is_narrator: bool
    ):
        """Toggle narrator mode for a persona."""
        # Verify persona exists
        persona = bot.agent_core.persona_loader.get_persona(persona_id)
        if not persona:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available[:10])}"
                ),
                ephemeral=True,
            )
            return

        try:
            # Update the is_narrator flag
            persona.is_narrator = is_narrator

            # Save back to metadata.json
            success = bot.agent_core.persona_loader.update_persona(
                persona_id, persona.to_dict()
            )

            if success:
                # Reload the persona to clear cache
                bot.agent_core.persona_loader.reload_persona(persona_id)

                status = "ENABLED" if is_narrator else "DISABLED"
                mode_description = (
                    "This persona will now act as an omniscient environmental narrator with no physical body."
                    if is_narrator
                    else "This persona will now act as a standard character with a physical body."
                )

                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"✅ **Narrator Mode {status}** for **{persona.name}**\n\n"
                        f"{mode_description}\n\n"
                        f"Reload this persona for changes to take effect in active sessions."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    ResponseFormatter.error(
                        f"Failed to update narrator status for '{persona_id}'. Check logs for details."
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Error setting narrator status: {str(e)}"),
                ephemeral=True,
            )

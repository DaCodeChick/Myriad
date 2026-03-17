"""
Lives command handlers for timeline/branching management.

Provides slash commands for managing alternate timelines (Lives).
"""

import discord
from discord import app_commands

from adapters.commands.base import ResponseFormatter


def _get_roleplay_feature(bot):
    """Get roleplay feature from bot, or None if not enabled."""
    return bot.agent_core.features.get("roleplay")


class ConfirmationView(discord.ui.View):
    """Generic confirmation dialog with Yes/No buttons."""

    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.value: bool | None = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


def register_lives_commands(bot) -> None:
    """
    Register lives (timeline branching) commands to the bot.

    Args:
        bot: MyriadDiscordBot instance
    """
    roleplay = _get_roleplay_feature(bot)
    if not roleplay or not roleplay.lives_engine:
        return  # Lives system not enabled

    life_group = app_commands.Group(
        name="life", description="Manage alternate timelines (Lives)"
    )

    @life_group.command(name="new", description="Create a new timeline")
    @app_commands.describe(
        name="Name for the new timeline", description="Description of this timeline"
    )
    async def life_new(interaction: discord.Interaction, name: str, description: str):
        """Create a new life/timeline."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        # Confirmation
        view = ConfirmationView()
        await interaction.response.send_message(
            f"Create new timeline **{name}**?\n"
            f"Description: {description}\n\n"
            f"This will create a fresh timeline branch.",
            view=view,
            ephemeral=True,
        )

        await view.wait()

        if view.value:
            try:
                life_id = _get_roleplay_feature(bot).lives_engine.create_life(
                    user_id=user_id,
                    persona_id=persona.persona_id,
                    name=name,
                    description=description,
                )
                await interaction.edit_original_response(
                    content=ResponseFormatter.success(
                        f"Created new timeline: **{name}** (ID: {life_id})"
                    ),
                    view=None,
                )
            except Exception as e:
                await interaction.edit_original_response(
                    content=ResponseFormatter.error(
                        f"Failed to create timeline: {str(e)}"
                    ),
                    view=None,
                )
        else:
            await interaction.edit_original_response(content="Cancelled.", view=None)

    @life_group.command(name="switch", description="Switch to a different timeline")
    @app_commands.describe(name="Name of the timeline to switch to")
    async def life_switch(interaction: discord.Interaction, name: str):
        """Switch to a different life/timeline."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        try:
            _get_roleplay_feature(bot).lives_engine.switch_life(
                user_id=user_id, persona_id=persona.persona_id, life_name=name
            )
            await interaction.response.send_message(
                ResponseFormatter.success(f"Switched to timeline: **{name}**"),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to switch timeline: {str(e)}"),
                ephemeral=True,
            )

    @life_group.command(name="list", description="List all timelines")
    async def life_list(interaction: discord.Interaction):
        """List all lives/timelines for the user."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        lives = _get_roleplay_feature(bot).lives_engine.list_lives(
            user_id=user_id, persona_id=persona.persona_id
        )

        if not lives:
            await interaction.response.send_message(
                "No timelines found.", ephemeral=True
            )
            return

        lines = ["**Your Timelines:**\n"]
        for life in lives:
            active_marker = " ✓ **[ACTIVE]**" if life["is_active"] else ""
            lines.append(
                f"• **{life['name']}**{active_marker}\n  _{life['description']}_"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @life_group.command(name="delete", description="Delete a timeline")
    @app_commands.describe(name="Name of the timeline to delete")
    async def life_delete(interaction: discord.Interaction, name: str):
        """Delete a life/timeline."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        # Confirmation
        view = ConfirmationView()
        await interaction.response.send_message(
            f"⚠️ Delete timeline **{name}**?\n\n"
            f"This will permanently delete all messages and save states in this timeline.",
            view=view,
            ephemeral=True,
        )

        await view.wait()

        if view.value:
            try:
                _get_roleplay_feature(bot).lives_engine.delete_life(
                    user_id=user_id, persona_id=persona.persona_id, life_name=name
                )
                await interaction.edit_original_response(
                    content=ResponseFormatter.success(f"Deleted timeline: **{name}**"),
                    view=None,
                )
            except Exception as e:
                await interaction.edit_original_response(
                    content=ResponseFormatter.error(
                        f"Failed to delete timeline: {str(e)}"
                    ),
                    view=None,
                )
        else:
            await interaction.edit_original_response(content="Cancelled.", view=None)

    bot.tree.add_command(life_group)

"""
Save states command handlers for checkpoint/rewind management.

Provides slash commands for managing save states (memory checkpoints).
"""

import discord
from discord import app_commands

from adapters.commands.base import ResponseFormatter


class BranchOrForgetView(discord.ui.View):
    """Save state load dialog with BRANCH/FORGET choice."""

    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.value: str | None = None  # "branch", "forget", or None

    @discord.ui.button(
        label="Save as New Branch", style=discord.ButtonStyle.primary, emoji="🌿"
    )
    async def branch(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "branch"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(
        label="Forget Forever", style=discord.ButtonStyle.danger, emoji="🗑️"
    )
    async def forget(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "forget"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = None
        self.stop()
        await interaction.response.defer()


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


def register_saves_commands(bot):
    """
    Register save states (checkpoint/rewind) commands to the bot.

    Args:
        bot: MyriadDiscordBot instance
    """
    if not bot.agent_core.save_states_engine:
        return  # Save states system not enabled

    memory_group = app_commands.Group(
        name="memory", description="Manage save states (Memories)"
    )

    @memory_group.command(name="save", description="Create a save state")
    @app_commands.describe(
        name="Name for this save state",
        description="Description of this checkpoint",
    )
    async def memory_save(
        interaction: discord.Interaction, name: str, description: str
    ):
        """Create a save state at the current message."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        # Get active life
        active_life = bot.agent_core.lives_engine.get_active_life(
            user_id=user_id, persona_id=persona.persona_id
        )

        if not active_life:
            await interaction.response.send_message(
                "No active timeline found.", ephemeral=True
            )
            return

        life_id = active_life["life_id"]

        # Get latest message ID as the checkpoint
        checkpoint_message_id = bot.agent_core.save_states_engine.get_latest_message_id(
            life_id=life_id
        )

        if not checkpoint_message_id:
            await interaction.response.send_message(
                "No messages found in this timeline to save.", ephemeral=True
            )
            return

        try:
            save_id = bot.agent_core.save_states_engine.create_save_state(
                life_id=life_id,
                name=name,
                description=description,
                checkpoint_message_id=checkpoint_message_id,
            )
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Created save state: **{name}** (ID: {save_id})"
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to create save state: {str(e)}"),
                ephemeral=True,
            )

    @memory_group.command(name="load", description="Load a save state")
    @app_commands.describe(name="Name of the save state to load")
    async def memory_load(interaction: discord.Interaction, name: str):
        """Load a save state with BRANCH/FORGET choice."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        # Get active life
        active_life = bot.agent_core.lives_engine.get_active_life(
            user_id=user_id, persona_id=persona.persona_id
        )

        if not active_life:
            await interaction.response.send_message(
                "No active timeline found.", ephemeral=True
            )
            return

        life_id = active_life["life_id"]

        # Get save state
        try:
            save_state = bot.agent_core.save_states_engine.get_save_state(
                life_id=life_id, name=name
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Save state not found: {str(e)}"),
                ephemeral=True,
            )
            return

        # Count messages to be affected
        messages_count = (
            bot.agent_core.save_states_engine.count_messages_after_checkpoint(
                life_id=life_id,
                checkpoint_message_id=save_state["checkpoint_message_id"],
            )
        )

        # Show BRANCH/FORGET dialog
        view = BranchOrForgetView()
        await interaction.response.send_message(
            f"⚠️ Loading save state **{name}** will affect {messages_count} messages.\n\n"
            f"**What would you like to do?**\n"
            f"🌿 **Save as New Branch**: Current timeline becomes a new branch, then rewind\n"
            f"🗑️ **Forget Forever**: Delete all messages after this checkpoint (irreversible)",
            view=view,
            ephemeral=True,
        )

        await view.wait()

        if view.value == "branch":
            # Save current timeline as a new branch
            try:
                new_life_name = f"{active_life['name']} (branch)"
                new_life_id = bot.agent_core.lives_engine.create_life(
                    user_id=user_id,
                    persona_id=persona.persona_id,
                    name=new_life_name,
                    description=f"Branch from {active_life['name']} before loading save state '{name}'",
                )

                # Clone all memories to the new life
                bot.agent_core.memory_matrix.clone_life_memories(
                    source_life_id=life_id, target_life_id=new_life_id
                )

                # Delete messages after checkpoint in original life
                deleted_count = (
                    bot.agent_core.memory_matrix.delete_memories_after_checkpoint(
                        life_id=life_id,
                        checkpoint_message_id=save_state["checkpoint_message_id"],
                    )
                )

                await interaction.edit_original_response(
                    content=ResponseFormatter.success(
                        f"Created branch **{new_life_name}** (ID: {new_life_id})\n"
                        f"Rewound timeline to save state **{name}** ({deleted_count} messages removed)"
                    ),
                    view=None,
                )
            except Exception as e:
                await interaction.edit_original_response(
                    content=ResponseFormatter.error(
                        f"Failed to branch and load: {str(e)}"
                    ),
                    view=None,
                )

        elif view.value == "forget":
            # Delete messages after checkpoint (permanent)
            try:
                deleted_count = (
                    bot.agent_core.memory_matrix.delete_memories_after_checkpoint(
                        life_id=life_id,
                        checkpoint_message_id=save_state["checkpoint_message_id"],
                    )
                )
                await interaction.edit_original_response(
                    content=ResponseFormatter.success(
                        f"Loaded save state **{name}** ({deleted_count} messages permanently deleted)"
                    ),
                    view=None,
                )
            except Exception as e:
                await interaction.edit_original_response(
                    content=ResponseFormatter.error(f"Failed to load: {str(e)}"),
                    view=None,
                )
        else:
            await interaction.edit_original_response(content="Cancelled.", view=None)

    @memory_group.command(name="list", description="List all save states")
    async def memory_list(interaction: discord.Interaction):
        """List all save states in the current timeline."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        # Get active life
        active_life = bot.agent_core.lives_engine.get_active_life(
            user_id=user_id, persona_id=persona.persona_id
        )

        if not active_life:
            await interaction.response.send_message(
                "No active timeline found.", ephemeral=True
            )
            return

        life_id = active_life["life_id"]

        save_states = bot.agent_core.save_states_engine.list_save_states(
            life_id=life_id
        )

        if not save_states:
            await interaction.response.send_message(
                "No save states found in this timeline.", ephemeral=True
            )
            return

        lines = ["**Save States in Current Timeline:**\n"]
        for save in save_states:
            lines.append(
                f"• **{save['name']}** (ID: {save['save_id']})\n  _{save['description']}_"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @memory_group.command(name="delete", description="Delete a save state")
    @app_commands.describe(name="Name of the save state to delete")
    async def memory_delete(interaction: discord.Interaction, name: str):
        """Delete a save state."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if not persona:
            await interaction.response.send_message(
                "You don't have an active persona. Use `/swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        # Get active life
        active_life = bot.agent_core.lives_engine.get_active_life(
            user_id=user_id, persona_id=persona.persona_id
        )

        if not active_life:
            await interaction.response.send_message(
                "No active timeline found.", ephemeral=True
            )
            return

        life_id = active_life["life_id"]

        # Confirmation
        view = ConfirmationView()
        await interaction.response.send_message(
            f"Delete save state **{name}**?\n\n"
            f"This only deletes the checkpoint marker, not the messages.",
            view=view,
            ephemeral=True,
        )

        await view.wait()

        if view.value:
            try:
                bot.agent_core.save_states_engine.delete_save_state(
                    life_id=life_id, name=name
                )
                await interaction.edit_original_response(
                    content=ResponseFormatter.success(
                        f"Deleted save state: **{name}**"
                    ),
                    view=None,
                )
            except Exception as e:
                await interaction.edit_original_response(
                    content=ResponseFormatter.error(
                        f"Failed to delete save state: {str(e)}"
                    ),
                    view=None,
                )
        else:
            await interaction.edit_original_response(content="Cancelled.", view=None)

    bot.tree.add_command(memory_group)

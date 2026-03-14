"""
User Mask management commands for Discord.

Handles creating, wearing, and managing user personas (masks) that the AI will recognize.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_mask_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all mask-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    # Mask Management Commands
    mask_group = app_commands.Group(
        name="mask", description="User persona (mask) management commands"
    )

    @mask_group.command(
        name="create",
        description="Create a new user persona (mask)",
    )
    @app_commands.describe(
        name="The name of your persona/character",
        description="A brief description of this character",
        background="Optional: Detailed lore/background for this character",
    )
    async def create_mask(
        interaction: discord.Interaction,
        name: str,
        description: str,
        background: str = None,
    ):
        """Create a new user persona."""
        user_id = str(interaction.user.id)

        try:
            mask = bot.agent_core.user_mask_manager.create_mask(
                user_id=user_id,
                name=name,
                description=description,
                background=background,
            )

            bg_info = ""
            if background:
                bg_info = f"\n• Background: {len(background)} characters"

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Created new mask: **{mask.name}**\n"
                    f"• Description: {description}"
                    f"{bg_info}\n\n"
                    f"Use `/mask wear {name}` to activate this persona."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to create mask: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="wear",
        description="Activate a user persona (the AI will recognize you as this character)",
    )
    @app_commands.describe(name="The name of the mask to wear")
    async def wear_mask(interaction: discord.Interaction, name: str):
        """Activate a user persona."""
        user_id = str(interaction.user.id)

        try:
            # Get the mask by name
            mask = bot.agent_core.user_mask_manager.get_mask(user_id, name)

            if not mask:
                # List available masks for the user
                masks = bot.agent_core.user_mask_manager.list_user_masks(user_id)
                if masks:
                    mask_list = ", ".join([f"'{m.name}'" for m in masks])
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Mask '{name}' not found.\n"
                            f"Your available masks: {mask_list}"
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Mask '{name}' not found. You haven't created any masks yet.\n"
                            f"Use `/mask create` to create one."
                        ),
                        ephemeral=True,
                    )
                return

            # Set the mask as active
            bot.agent_core.user_mask_manager.set_active_mask(user_id, mask.id)

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Now wearing mask: **{mask.name}**\n"
                    f"The AI will now recognize you as this character.\n\n"
                    f"Use `/mask remove` to return to your normal identity."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to wear mask: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="remove",
        description="Remove your active mask and return to normal identity",
    )
    async def remove_mask(interaction: discord.Interaction):
        """Deactivate the current mask."""
        user_id = str(interaction.user.id)

        try:
            # Get current mask name before removing
            active_mask = bot.agent_core.user_mask_manager.get_active_mask(user_id)

            # Clear the active mask
            bot.agent_core.user_mask_manager.set_active_mask(user_id, None)

            if active_mask:
                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"Removed mask: **{active_mask.name}**\n"
                        f"You are now recognized as a standard user."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    ResponseFormatter.warning("You weren't wearing any mask."),
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to remove mask: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="list",
        description="Show all your saved user personas",
    )
    async def list_masks(interaction: discord.Interaction):
        """List all user personas."""
        user_id = str(interaction.user.id)

        try:
            masks = bot.agent_core.user_mask_manager.list_user_masks(user_id)
            active_mask = bot.agent_core.user_mask_manager.get_active_mask(user_id)

            if not masks:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "You haven't created any masks yet.\n"
                        "Use `/mask create` to create your first persona."
                    ),
                    ephemeral=True,
                )
                return

            # Build the list
            mask_list = []
            for mask in masks:
                active_indicator = (
                    " 🎭 **(ACTIVE)**"
                    if active_mask and mask.id == active_mask.id
                    else ""
                )
                bg_indicator = " 📖" if mask.background else ""
                mask_list.append(
                    f"• **{mask.name}**{active_indicator}{bg_indicator}\n  _{mask.description}_"
                )

            response = "**Your Masks:**\n\n" + "\n\n".join(mask_list)
            response += "\n\n📖 = Has background lore"
            response += "\n\nUse `/mask wear <name>` to activate a mask."

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to list masks: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="view",
        description="View details of a specific mask",
    )
    @app_commands.describe(name="The name of the mask to view")
    async def view_mask(interaction: discord.Interaction, name: str):
        """View details of a specific mask."""
        user_id = str(interaction.user.id)

        try:
            mask = bot.agent_core.user_mask_manager.get_mask(user_id, name)

            if not mask:
                await interaction.response.send_message(
                    ResponseFormatter.error(f"Mask '{name}' not found."),
                    ephemeral=True,
                )
                return

            response = (
                f"**Mask: {mask.name}**\n\n**Description:**\n{mask.description}\n"
            )

            if mask.background:
                # If background is too long, truncate and offer to view separately
                if len(mask.background) <= 800:
                    response += f"\n**Background:**\n{mask.background}"
                else:
                    preview = mask.background[:800] + "..."
                    response += f"\n**Background (preview):**\n{preview}\n\n"
                    response += f"_Full background: {len(mask.background)} characters_"
            else:
                response += "\n**Background:** _None set_"

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to view mask: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="edit",
        description="Update the description or background of a mask",
    )
    @app_commands.describe(
        name="The name of the mask to edit",
        description="New description (leave empty to keep current)",
        background="New background (leave empty to keep current)",
    )
    async def edit_mask(
        interaction: discord.Interaction,
        name: str,
        description: str = None,
        background: str = None,
    ):
        """Edit an existing mask."""
        user_id = str(interaction.user.id)

        try:
            mask = bot.agent_core.user_mask_manager.get_mask(user_id, name)

            if not mask:
                await interaction.response.send_message(
                    ResponseFormatter.error(f"Mask '{name}' not found."),
                    ephemeral=True,
                )
                return

            if not description and not background:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "No changes provided. Specify at least description or background."
                    ),
                    ephemeral=True,
                )
                return

            # Update the mask
            bot.agent_core.user_mask_manager.update_mask(
                mask_id=mask.id,
                description=description,
                background=background,
            )

            changes = []
            if description:
                changes.append(f"description updated")
            if background:
                changes.append(f"background updated ({len(background)} chars)")

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Updated mask **{mask.name}**:\n• " + "\n• ".join(changes)
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to edit mask: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="delete",
        description="Permanently delete a mask",
    )
    @app_commands.describe(name="The name of the mask to delete")
    async def delete_mask(interaction: discord.Interaction, name: str):
        """Delete a mask permanently."""
        user_id = str(interaction.user.id)

        try:
            mask = bot.agent_core.user_mask_manager.get_mask(user_id, name)

            if not mask:
                await interaction.response.send_message(
                    ResponseFormatter.error(f"Mask '{name}' not found."),
                    ephemeral=True,
                )
                return

            # Check if it's the active mask
            active_mask = bot.agent_core.user_mask_manager.get_active_mask(user_id)
            if active_mask and active_mask.id == mask.id:
                # Remove it first
                bot.agent_core.user_mask_manager.set_active_mask(user_id, None)

            # Delete the mask
            bot.agent_core.user_mask_manager.delete_mask(mask.id)

            await interaction.response.send_message(
                ResponseFormatter.success(f"Deleted mask: **{mask.name}**"),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to delete mask: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="whoami",
        description="Check which mask you're currently wearing",
    )
    async def mask_whoami(interaction: discord.Interaction):
        """Show the currently active mask."""
        user_id = str(interaction.user.id)

        try:
            active_mask = bot.agent_core.user_mask_manager.get_active_mask(user_id)

            if active_mask:
                response = (
                    f"**Currently wearing:**\n"
                    f"• Name: **{active_mask.name}**\n"
                    f"• Description: {active_mask.description}\n"
                )
                if active_mask.background:
                    response += (
                        f"• Background: ✓ Defined ({len(active_mask.background)} chars)"
                    )
                else:
                    response += "• Background: _None_"

                response += (
                    f"\n\nUse `/mask view {active_mask.name}` to see full details."
                )
            else:
                response = ResponseFormatter.warning(
                    "You're not wearing any mask.\n"
                    "Use `/mask list` to see your masks, or `/mask create` to make one."
                )

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to check active mask: {str(e)}"),
                ephemeral=True,
            )

    # Register the mask group
    bot.tree.add_command(mask_group)

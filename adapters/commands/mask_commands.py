"""
User Mask management commands for Discord.

User masks are simply personas from the personas/user_masks/ directory.
Users can wear them as their character identity in conversations.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING, Optional

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
        name="wear",
        description="Wear a persona as your character (e.g., 'user_masks/schala')",
    )
    @app_commands.describe(
        persona_id="The persona ID to wear (e.g., 'user_masks/schala')"
    )
    async def wear_mask(interaction: discord.Interaction, persona_id: str):
        """Activate a user persona."""
        user_id = str(interaction.user.id)

        try:
            # Try to load the persona
            persona = bot.agent_core.persona_loader.load_persona(persona_id)

            if not persona:
                # List available user masks
                all_personas = bot.agent_core.persona_loader.list_available_personas()
                user_masks = [p for p in all_personas if p.startswith("user_masks/")]

                if user_masks:
                    mask_list = ", ".join([f"'{m}'" for m in user_masks[:5]])
                    more = (
                        f" and {len(user_masks) - 5} more"
                        if len(user_masks) > 5
                        else ""
                    )
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Persona '{persona_id}' not found.\n"
                            f"Available user masks: {mask_list}{more}"
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Persona '{persona_id}' not found.\n"
                            f"No user masks exist yet in personas/user_masks/"
                        ),
                        ephemeral=True,
                    )
                return

            # Set the mask as active
            bot.agent_core.user_mask_manager.set_active_mask(user_id, persona_id)

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Now wearing: **{persona.name}**\n"
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
            # Get current mask before removing
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
        description="List all available user masks (personas in user_masks/)",
    )
    async def list_masks(interaction: discord.Interaction):
        """List all available user masks."""
        try:
            user_id = str(interaction.user.id)
            active_mask = bot.agent_core.user_mask_manager.get_active_mask(user_id)

            # Get all personas and filter for user_masks
            all_personas = bot.agent_core.persona_loader.list_available_personas()
            user_masks = [p for p in all_personas if p.startswith("user_masks/")]

            if not user_masks:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "No user masks found.\n"
                        "Create personas in `personas/user_masks/` directory."
                    ),
                    ephemeral=True,
                )
                return

            # Load and display each mask
            mask_list = []
            for persona_id in sorted(user_masks):
                persona = bot.agent_core.persona_loader.load_persona(persona_id)
                if persona:
                    active_indicator = (
                        " 🎭 **(ACTIVE)**"
                        if active_mask and persona.persona_id == active_mask.persona_id
                        else ""
                    )
                    bg_indicator = " 📖" if persona.background else ""
                    mask_list.append(
                        f"• **{persona.name}** (`{persona_id}`){active_indicator}{bg_indicator}\n"
                        f"  _{persona.system_prompt[:100]}..._"
                    )

            response = "**Available User Masks:**\n\n" + "\n\n".join(mask_list)
            response += "\n\n📖 = Has background lore"
            response += "\n\nUse `/mask wear <persona_id>` to wear a mask."

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to list masks: {str(e)}"),
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
                response = f"**Currently wearing: {active_mask.name}**\n\n"
                response += f"**Persona ID:** `{active_mask.persona_id}`\n\n"
                response += f"**Character:**\n{active_mask.system_prompt}\n"

                if active_mask.background:
                    preview = (
                        active_mask.background[:200] + "..."
                        if len(active_mask.background) > 200
                        else active_mask.background
                    )
                    response += f"\n**Background:**\n{preview}"

                await interaction.response.send_message(response, ephemeral=True)
            else:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "You are not wearing any mask.\n"
                        "Use `/mask wear <persona_id>` to put one on, or\n"
                        "Use `/mask list` to see available masks."
                    ),
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to check mask status: {str(e)}"),
                ephemeral=True,
            )

    # Register the group
    bot.tree.add_command(mask_group)

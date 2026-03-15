"""
User Mask management commands for Discord.

User masks are personas that users wear as their character identity.
ANY persona can be worn as a mask - there's no separate "user_masks" folder anymore.
When a user wears a persona, the AI recognizes them as that character.
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
        description="Wear any persona as your character identity",
    )
    @app_commands.describe(
        persona_id="The persona ID to wear (e.g., 'chrono/schala', 'generic/coding_mentor')"
    )
    async def wear_mask(interaction: discord.Interaction, persona_id: str):
        """Activate a user persona."""
        user_id = str(interaction.user.id)

        try:
            # Try to load the persona
            persona = bot.agent_core.persona_loader.load_persona(persona_id)

            if not persona:
                # List available personas (show first 10)
                all_personas = bot.agent_core.persona_loader.list_available_personas()

                if all_personas:
                    persona_list = ", ".join([f"'{p}'" for p in all_personas[:10]])
                    more = (
                        f" (and {len(all_personas) - 10} more)"
                        if len(all_personas) > 10
                        else ""
                    )
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Persona '{persona_id}' not found.\n\n"
                            f"**Examples:** {persona_list}{more}\n\n"
                            f"Use `/personas` to see all available personas."
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Persona '{persona_id}' not found.\n"
                            f"No personas exist yet in personas/ folder."
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
        description="List all available personas (any can be worn as a mask)",
    )
    async def list_masks(interaction: discord.Interaction):
        """List all available personas that can be worn."""
        try:
            user_id = str(interaction.user.id)
            active_mask = bot.agent_core.user_mask_manager.get_active_mask(user_id)

            # Get all personas
            all_personas = bot.agent_core.persona_loader.list_available_personas()

            if not all_personas:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "No personas found.\nCreate personas in `personas/` directory."
                    ),
                    ephemeral=True,
                )
                return

            # Load and display personas (limit to first 15 for brevity)
            persona_list = []
            for persona_id in sorted(all_personas[:15]):
                persona = bot.agent_core.persona_loader.load_persona(persona_id)
                if persona:
                    active_indicator = (
                        " 🎭 **(WEARING)**"
                        if active_mask and persona.persona_id == active_mask.persona_id
                        else ""
                    )
                    bg_indicator = " 📖" if persona.background else ""
                    img_indicator = " 🖼️" if persona.cached_appearance else ""
                    persona_list.append(
                        f"• **{persona.name}** (`{persona_id}`){active_indicator}{bg_indicator}{img_indicator}\n"
                        f"  _{persona.system_prompt[:80]}..._"
                    )

            response = "**Available Personas (any can be worn):**\n\n" + "\n\n".join(
                persona_list
            )

            if len(all_personas) > 15:
                response += f"\n\n_...and {len(all_personas) - 15} more. Use `/personas` to see all._"

            response += "\n\n📖 = Has background lore"
            response += "\n🖼️ = Has appearance images"
            response += "\n\nUse `/mask wear <persona_id>` to wear a persona."

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to list personas: {str(e)}"),
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

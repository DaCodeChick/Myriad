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


def _get_roleplay_feature(bot):
    """Get roleplay feature from bot, or None if not enabled."""
    return bot.agent_core.features.get("roleplay")


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
        description="Wear any persona as your character identity (adds to ensemble)",
    )
    @app_commands.describe(
        persona_id="The persona ID to wear (e.g., 'chrono/schala', 'generic/coding_mentor')"
    )
    async def wear_mask(interaction: discord.Interaction, persona_id: str):
        """Activate a user persona (adds to ensemble)."""
        user_id = str(interaction.user.id)

        # Check if roleplay feature is enabled
        roleplay = _get_roleplay_feature(bot)
        if (
            not roleplay
            or not roleplay.persona_loader
            or not roleplay.user_mask_manager
        ):
            await interaction.response.send_message(
                ResponseFormatter.error("Roleplay feature is not enabled."),
                ephemeral=True,
            )
            return

        try:
            # Try to load the persona
            persona = roleplay.persona_loader.load_persona(persona_id)

            if not persona:
                # List available personas (show first 10)
                all_personas = roleplay.persona_loader.list_available_personas()

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

            # Add to ensemble (append mode)
            success = roleplay.user_mask_manager.add_active_mask(user_id, persona_id)

            if success:
                # Get all active masks
                active_masks = roleplay.user_mask_manager.get_active_masks(user_id)
                ensemble_status = (
                    f"\n\n**User Ensemble Active** ({len(active_masks)} masks worn)"
                    if len(active_masks) > 1
                    else ""
                )

                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"Now wearing: **{persona.name}**\n"
                        f"The AI will now recognize you as this character.{ensemble_status}\n\n"
                        f"Use `/mask remove {persona_id}` to remove this mask."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        f"You are already wearing mask '{persona_id}'."
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
        description="Remove a specific mask from your identity",
    )
    @app_commands.describe(
        persona_id="The persona ID to remove (optional - removes all if not specified)"
    )
    async def remove_mask(interaction: discord.Interaction, persona_id: str = ""):
        """Deactivate a specific mask or all masks."""
        user_id = str(interaction.user.id)

        # Check if roleplay feature is enabled
        roleplay = _get_roleplay_feature(bot)
        if not roleplay or not roleplay.user_mask_manager:
            await interaction.response.send_message(
                ResponseFormatter.error("Roleplay feature is not enabled."),
                ephemeral=True,
            )
            return

        try:
            # If no persona_id specified, remove all masks (legacy behavior)
            if not persona_id or persona_id.strip() == "":
                active_masks = roleplay.user_mask_manager.get_active_masks(user_id)
                count = len(active_masks)

                # Clear all masks
                roleplay.user_mask_manager.clear_active_masks(user_id)

                if count > 0:
                    await interaction.response.send_message(
                        ResponseFormatter.success(
                            f"Removed all masks ({count} mask(s)).\n"
                            f"You are now recognized as a standard user."
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        ResponseFormatter.warning("You weren't wearing any mask."),
                        ephemeral=True,
                    )
                return

            # Remove specific mask
            success = roleplay.user_mask_manager.remove_active_mask(user_id, persona_id)

            if success:
                active_masks = roleplay.user_mask_manager.get_active_masks(user_id)
                remaining_status = (
                    f"\n\n**{len(active_masks)} mask(s) still worn**"
                    if active_masks
                    else "\n\nYou are now recognized as a standard user."
                )

                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"Removed mask: `{persona_id}`{remaining_status}"
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        f"You weren't wearing mask '{persona_id}'."
                    ),
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to remove mask: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="clear",
        description="Remove all masks and return to normal identity",
    )
    async def clear_masks(interaction: discord.Interaction):
        """Clear all active masks."""
        user_id = str(interaction.user.id)

        # Check if roleplay feature is enabled
        roleplay = _get_roleplay_feature(bot)
        if not roleplay or not roleplay.user_mask_manager:
            await interaction.response.send_message(
                ResponseFormatter.error("Roleplay feature is not enabled."),
                ephemeral=True,
            )
            return

        try:
            # Get count before clearing
            active_masks = roleplay.user_mask_manager.get_active_masks(user_id)
            count = len(active_masks)

            roleplay.user_mask_manager.clear_active_masks(user_id)

            if count > 0:
                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"Removed all masks ({count} mask(s)).\n"
                        f"You are now recognized as a standard user."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    ResponseFormatter.warning("You weren't wearing any masks."),
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to clear masks: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="list_active",
        description="Show all masks you're currently wearing",
    )
    async def list_active_masks(interaction: discord.Interaction):
        """List all active masks in the user ensemble."""
        user_id = str(interaction.user.id)

        # Check if roleplay feature is enabled
        roleplay = _get_roleplay_feature(bot)
        if not roleplay or not roleplay.user_mask_manager:
            await interaction.response.send_message(
                ResponseFormatter.error("Roleplay feature is not enabled."),
                ephemeral=True,
            )
            return

        try:
            active_masks = roleplay.user_mask_manager.get_active_masks(user_id)

            if not active_masks:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "You are not wearing any masks.\n\n"
                        "Use `/mask wear <persona_id>` to put one on, or\n"
                        "Use `/mask list` to see available masks."
                    ),
                    ephemeral=True,
                )
                return

            # Build response
            response = "**Currently Wearing:**\n\n"

            for mask in active_masks:
                bg_indicator = " 📖" if mask.background else ""
                img_indicator = " 🖼️" if mask.cached_appearance else ""

                preview = (
                    mask.system_prompt[:80] + "..."
                    if len(mask.system_prompt) > 80
                    else mask.system_prompt
                )

                response += (
                    f"• **{mask.name}** (`{mask.persona_id}`){bg_indicator}{img_indicator}\n"
                    f"  _{preview}_\n\n"
                )

            if len(active_masks) > 1:
                response += f"**🎭 User Ensemble Active** ({len(active_masks)} masks)\n"
                response += (
                    "The AI will recognize you as embodying multiple characters.\n\n"
                )

            response += "📖 = Has background lore\n"
            response += "🖼️ = Has appearance images"

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to list active masks: {str(e)}"),
                ephemeral=True,
            )

    @mask_group.command(
        name="list",
        description="List all available personas (any can be worn as a mask)",
    )
    async def list_masks(interaction: discord.Interaction):
        """List all available personas that can be worn."""
        user_id = str(interaction.user.id)

        # Check if roleplay feature is enabled
        roleplay = _get_roleplay_feature(bot)
        if (
            not roleplay
            or not roleplay.persona_loader
            or not roleplay.user_mask_manager
        ):
            await interaction.response.send_message(
                ResponseFormatter.error("Roleplay feature is not enabled."),
                ephemeral=True,
            )
            return

        try:
            active_mask = roleplay.user_mask_manager.get_active_mask(user_id)

            # Get all personas
            all_personas = roleplay.persona_loader.list_available_personas()

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
                persona = roleplay.persona_loader.load_persona(persona_id)
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
        description="Check which mask(s) you're currently wearing",
    )
    async def mask_whoami(interaction: discord.Interaction):
        """Show the currently active mask(s)."""
        user_id = str(interaction.user.id)

        # Check if roleplay feature is enabled
        roleplay = _get_roleplay_feature(bot)
        if not roleplay or not roleplay.user_mask_manager:
            await interaction.response.send_message(
                ResponseFormatter.error("Roleplay feature is not enabled."),
                ephemeral=True,
            )
            return

        try:
            active_masks = roleplay.user_mask_manager.get_active_masks(user_id)

            if not active_masks:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "You are not wearing any mask.\n"
                        "Use `/mask wear <persona_id>` to put one on, or\n"
                        "Use `/mask list` to see available masks."
                    ),
                    ephemeral=True,
                )
                return

            # If multiple masks (ensemble mode)
            if len(active_masks) > 1:
                response = (
                    f"**🎭 User Ensemble Active** ({len(active_masks)} masks)\n\n"
                )

                for mask in active_masks:
                    bg_indicator = " 📖" if mask.background else ""
                    img_indicator = " 🖼️" if mask.cached_appearance else ""

                    response += f"**{mask.name}** (`{mask.persona_id}`){bg_indicator}{img_indicator}\n"
                    response += f"_{mask.system_prompt[:100]}..._\n"

                    if mask.background:
                        preview = (
                            mask.background[:150] + "..."
                            if len(mask.background) > 150
                            else mask.background
                        )
                        response += f"\n**Background:**\n{preview}\n"

                    response += "\n"

                response += "You are embodying multiple characters.\n"
                response += "\n📖 = Has background | 🖼️ = Has appearance images"

                await interaction.response.send_message(response, ephemeral=True)
            else:
                # Single mask mode
                active_mask = active_masks[0]
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
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to check mask status: {str(e)}"),
                ephemeral=True,
            )

    # Register the group
    bot.tree.add_command(mask_group)

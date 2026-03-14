"""
Persona management commands for Discord.

Handles persona switching, listing, and information display.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_persona_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all persona-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(name="swap", description="Switch to a different persona")
    @app_commands.describe(persona_id="The ID of the persona to switch to")
    async def swap_persona(interaction: discord.Interaction, persona_id: str):
        """Switch the user's active persona."""
        user_id = str(interaction.user.id)

        # Attempt to switch persona
        success = bot.agent_core.switch_persona(user_id, persona_id)

        if success:
            persona = bot.agent_core.get_active_persona(user_id)
            if persona:  # Type guard to satisfy type checker
                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"Switched to persona: **{persona.name}** (`{persona_id}`)"
                    ),
                    ephemeral=True,
                )
        else:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available)}"
                ),
                ephemeral=True,
            )

    @bot.tree.command(name="personas", description="List all available personas")
    async def list_personas_cmd(interaction: discord.Interaction):
        """List all available persona cartridges."""
        personas = bot.agent_core.list_personas()

        if personas:
            persona_list = "\n".join([f"• `{p}`" for p in personas])
            await interaction.response.send_message(
                f"**Available Personas:**\n{persona_list}\n\n"
                f"Use `/swap <persona_id>` to switch.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    "No personas found in the `personas/` directory."
                ),
                ephemeral=True,
            )

    @bot.tree.command(name="whoami", description="Check your current active persona")
    async def whoami(interaction: discord.Interaction):
        """Show the user's current active persona."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if persona:
            traits = (
                ", ".join(persona.personality_traits)
                if persona.personality_traits
                else "None"
            )

            # Build response with background info if available
            response = (
                f"**Current Persona:**\n"
                f"• ID: `{persona.persona_id}`\n"
                f"• Name: **{persona.name}**\n"
                f"• Traits: {traits}\n"
                f"• Temperature: {persona.temperature}\n"
                f"• Max Tokens: {persona.max_tokens}"
            )

            if persona.background:
                # Show "Has background" indicator with character count
                # User can use /persona view_background to see full text
                response += f"\n• Background: ✓ Defined ({len(persona.background)} chars) - use `/persona view_background {persona.persona_id}` to view"

            await interaction.response.send_message(
                response,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"You don't have an active persona.\n"
                f"Use `/swap <persona_id>` to select one.",
                ephemeral=True,
            )

    # Persona Background Management Commands
    persona_group = app_commands.Group(
        name="persona", description="Advanced persona management commands"
    )

    @persona_group.command(
        name="set_background",
        description="Set or update the background/lore for a persona",
    )
    @app_commands.describe(
        persona_id="The ID of the persona to update",
        background="The background/lore text (can be multiple paragraphs)",
    )
    async def set_persona_background(
        interaction: discord.Interaction, persona_id: str, background: str
    ):
        """Set or update the background field for an existing persona."""
        # Verify persona exists
        persona = bot.agent_core.persona_loader.get_persona(persona_id)
        if not persona:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available)}"
                ),
                ephemeral=True,
            )
            return

        # Update the background
        success = bot.agent_core.persona_loader.update_persona_background(
            persona_id, background
        )

        if success:
            # Reload the persona to clear cache
            bot.agent_core.persona_loader.reload_persona(persona_id)

            bg_preview = background[:100]
            if len(background) > 100:
                bg_preview += "..."

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Updated background for **{persona.name}** (`{persona_id}`):\n\n"
                    f"{bg_preview}\n\n"
                    f"Full length: {len(background)} characters"
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Failed to update background for '{persona_id}'. Check logs for details."
                ),
                ephemeral=True,
            )

    @persona_group.command(
        name="view_background",
        description="View the full background/lore for a persona",
    )
    @app_commands.describe(persona_id="The ID of the persona to view")
    async def view_persona_background(
        interaction: discord.Interaction, persona_id: str
    ):
        """View the complete background for a persona."""
        persona = bot.agent_core.persona_loader.get_persona(persona_id)
        if not persona:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available)}"
                ),
                ephemeral=True,
            )
            return

        if persona.background:
            # Split into chunks if too long for Discord (2000 char limit)
            background = persona.background

            if len(background) <= 1900:
                await interaction.response.send_message(
                    f"**Background for {persona.name}** (`{persona_id}`):\n\n{background}",
                    ephemeral=True,
                )
            else:
                # Send in chunks
                await interaction.response.send_message(
                    f"**Background for {persona.name}** (`{persona_id}`):\n\n{background[:1900]}",
                    ephemeral=True,
                )
                # Send remaining chunks as follow-up messages
                remaining = background[1900:]
                while remaining:
                    chunk = remaining[:1900]
                    remaining = remaining[1900:]
                    await interaction.followup.send(chunk, ephemeral=True)
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    f"**{persona.name}** (`{persona_id}`) does not have a background defined.\n\n"
                    f"Use `/persona set_background {persona_id} <text>` to add one."
                ),
                ephemeral=True,
            )

    @persona_group.command(
        name="clear_background", description="Remove the background/lore from a persona"
    )
    @app_commands.describe(persona_id="The ID of the persona to update")
    async def clear_persona_background(
        interaction: discord.Interaction, persona_id: str
    ):
        """Clear the background field from a persona."""
        persona = bot.agent_core.persona_loader.get_persona(persona_id)
        if not persona:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available)}"
                ),
                ephemeral=True,
            )
            return

        if not persona.background:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    f"**{persona.name}** (`{persona_id}`) already has no background."
                ),
                ephemeral=True,
            )
            return

        # Update with empty background (None)
        success = bot.agent_core.persona_loader.update_persona_background(
            persona_id, None
        )

        if success:
            bot.agent_core.persona_loader.reload_persona(persona_id)
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Cleared background for **{persona.name}** (`{persona_id}`)"
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Failed to clear background for '{persona_id}'. Check logs for details."
                ),
                ephemeral=True,
            )

    @persona_group.command(
        name="set_image",
        description="Process character image and cache physical appearance",
    )
    @app_commands.describe(
        persona_id="The ID of the persona to update",
        image="Character image attachment",
    )
    async def set_persona_image(
        interaction: discord.Interaction,
        persona_id: str,
        image: discord.Attachment,
    ):
        """Process a character image and cache the appearance description."""
        # Check if vision cache service is available
        if not hasattr(bot, "vision_cache_service") or bot.vision_cache_service is None:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    "Vision cache service is not configured. "
                    "Please set VISION_BASE_URL and VISION_MODEL in your environment."
                ),
                ephemeral=True,
            )
            return

        # Verify persona exists
        persona = bot.agent_core.persona_loader.get_persona(persona_id)
        if not persona:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available)}"
                ),
                ephemeral=True,
            )
            return

        # Check if attachment is an image
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message(
                ResponseFormatter.error(
                    "Attachment must be an image file (PNG, JPG, WEBP, etc.)"
                ),
                ephemeral=True,
            )
            return

        # Defer response since vision processing may take time
        await interaction.response.defer(ephemeral=True)

        try:
            # Download image bytes
            image_bytes = await image.read()

            # Determine image format
            image_format = (
                image.content_type.split("/")[1] if "/" in image.content_type else "png"
            )

            # Process image through vision model
            appearance_description = (
                bot.vision_cache_service.generate_appearance_description(
                    image_bytes, image_format
                )
            )

            if not appearance_description:
                await interaction.followup.send(
                    ResponseFormatter.error(
                        "Failed to process image. The vision model may be unavailable or returned an empty description."
                    ),
                    ephemeral=True,
                )
                return

            # Save to persona
            success = bot.agent_core.persona_loader.update_persona_appearance(
                persona_id, appearance_description
            )

            if success:
                # Reload persona to clear cache
                bot.agent_core.persona_loader.reload_persona(persona_id)

                await interaction.followup.send(
                    ResponseFormatter.success(
                        f"✅ Image processed and cached for **{persona.name}** (`{persona_id}`)!\n\n"
                        f"**Here is how the AI will see this character:**\n"
                        f"{appearance_description}\n\n"
                        f"This description will be injected into the system prompt whenever this persona is active."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    ResponseFormatter.error(
                        f"Failed to save appearance cache for '{persona_id}'. Check logs for details."
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Error processing image: {str(e)}"),
                ephemeral=True,
            )

    # Register the persona group
    bot.tree.add_command(persona_group)

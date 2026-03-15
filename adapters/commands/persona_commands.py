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

    @bot.tree.command(name="whoami", description="Check your current active persona(s)")
    async def whoami(interaction: discord.Interaction):
        """Show the user's current active persona(s)."""
        user_id = str(interaction.user.id)

        # Check for ensemble mode (multiple personas)
        active_personas = bot.agent_core.get_active_personas(user_id)

        if not active_personas:
            await interaction.response.send_message(
                f"You don't have an active persona.\n"
                f"Use `/swap <persona_id>` to select one, or\n"
                f"Use `/persona load <persona_id>` to load multiple personas.",
                ephemeral=True,
            )
            return

        # If ensemble mode (multiple personas)
        if len(active_personas) > 1:
            response = (
                f"**🎭 Ensemble Mode Active** ({len(active_personas)} personas)\n\n"
            )

            for persona in active_personas:
                traits = (
                    ", ".join(persona.personality_traits[:3])
                    if persona.personality_traits
                    else "None"
                )
                bg_indicator = " 📖" if persona.background else ""
                img_indicator = " 🖼️" if persona.cached_appearance else ""

                response += (
                    f"**{persona.name}** (`{persona.persona_id}`){bg_indicator}{img_indicator}\n"
                    f"• Traits: {traits}\n"
                    f"• Temp: {persona.temperature} | Tokens: {persona.max_tokens}\n\n"
                )

            response += "The AI is controlling multiple characters as Dungeon Master/Narrator.\n"
            response += "\n📖 = Has background | 🖼️ = Has appearance images"

            await interaction.response.send_message(response, ephemeral=True)
        else:
            # Single persona mode
            persona = active_personas[0]
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

    # Persona Background Management Commands
    persona_group = app_commands.Group(
        name="persona", description="Advanced persona management commands"
    )

    @persona_group.command(
        name="load",
        description="Load a persona into the ensemble (adds to active personas)",
    )
    @app_commands.describe(persona_id="The ID of the persona to load")
    async def load_persona(interaction: discord.Interaction, persona_id: str):
        """Load a persona into the ensemble."""
        user_id = str(interaction.user.id)

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

        # Add to ensemble
        success = bot.agent_core.add_active_persona(user_id, persona_id)

        if success:
            # Get all active personas
            active_personas = bot.agent_core.get_active_personas(user_id)
            ensemble_status = (
                f"\n\n**Ensemble Mode Active** ({len(active_personas)} personas loaded)"
                if len(active_personas) > 1
                else ""
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Loaded persona: **{persona.name}** (`{persona_id}`){ensemble_status}"
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning(f"Persona '{persona_id}' is already loaded."),
                ephemeral=True,
            )

    @persona_group.command(
        name="unload",
        description="Unload a specific persona from the ensemble",
    )
    @app_commands.describe(persona_id="The ID of the persona to unload")
    async def unload_persona(interaction: discord.Interaction, persona_id: str):
        """Remove a persona from the ensemble."""
        user_id = str(interaction.user.id)

        success = bot.agent_core.remove_active_persona(user_id, persona_id)

        if success:
            active_personas = bot.agent_core.get_active_personas(user_id)
            remaining_status = (
                f"\n\n**{len(active_personas)} persona(s) remaining**"
                if active_personas
                else "\n\n**No personas active**"
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Unloaded persona: `{persona_id}`{remaining_status}"
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning(f"Persona '{persona_id}' was not loaded."),
                ephemeral=True,
            )

    @persona_group.command(
        name="clear",
        description="Clear all active personas from the ensemble",
    )
    async def clear_personas(interaction: discord.Interaction):
        """Clear all active personas."""
        user_id = str(interaction.user.id)

        # Get count before clearing
        active_personas = bot.agent_core.get_active_personas(user_id)
        count = len(active_personas)

        bot.agent_core.clear_active_personas(user_id)

        if count > 0:
            await interaction.response.send_message(
                ResponseFormatter.success(f"Cleared {count} persona(s) from ensemble."),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning("No personas were active."),
                ephemeral=True,
            )

    @persona_group.command(
        name="list_active",
        description="Show all currently loaded personas in the ensemble",
    )
    async def list_active_personas(interaction: discord.Interaction):
        """List all active personas in the ensemble."""
        user_id = str(interaction.user.id)

        active_personas = bot.agent_core.get_active_personas(user_id)

        if not active_personas:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    "No personas are currently active.\n\n"
                    "Use `/persona load <persona_id>` to load one, or\n"
                    "Use `/swap <persona_id>` to switch to a single persona."
                ),
                ephemeral=True,
            )
            return

        # Build response
        response = "**Active Personas:**\n\n"

        for persona in active_personas:
            traits = (
                ", ".join(persona.personality_traits[:3])
                if persona.personality_traits
                else "None"
            )
            bg_indicator = " 📖" if persona.background else ""
            img_indicator = " 🖼️" if persona.cached_appearance else ""

            response += (
                f"• **{persona.name}** (`{persona.persona_id}`){bg_indicator}{img_indicator}\n"
                f"  Traits: {traits}\n\n"
            )

        if len(active_personas) > 1:
            response += (
                f"**🎭 Ensemble Mode Active** ({len(active_personas)} personas)\n"
            )
            response += "The AI is controlling multiple characters as Dungeon Master/Narrator.\n\n"

        response += "📖 = Has background lore\n"
        response += "🖼️ = Has appearance images"

        await interaction.response.send_message(response, ephemeral=True)

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
        name="add_image",
        description="Add an image to a persona folder (auto-generates appearance cache)",
    )
    @app_commands.describe(
        persona_id="The ID of the persona to update",
        image="Character image attachment",
        filename="Optional filename (default: uses attachment name)",
    )
    async def add_persona_image(
        interaction: discord.Interaction,
        persona_id: str,
        image: discord.Attachment,
        filename: str = "",
    ):
        """Add an image to a persona folder and trigger appearance regeneration."""
        import os
        from pathlib import Path

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
                    f"Available personas: {', '.join(available[:10])}"
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

        # Defer response since processing may take time
        await interaction.response.defer(ephemeral=True)

        try:
            # Download image bytes
            image_bytes = await image.read()

            # Determine filename - use provided filename or attachment name
            if filename and filename.strip():
                save_filename = filename.strip()
            else:
                save_filename = image.filename

            # Ensure proper extension
            if not any(
                save_filename.lower().endswith(ext)
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
            ):
                # Try to get extension from content type
                if image.content_type:
                    ext = image.content_type.split("/")[1]
                    if ext == "jpeg":
                        ext = "jpg"
                    save_filename = f"{save_filename}.{ext}"
                else:
                    save_filename = f"{save_filename}.png"

            # Build path to persona folder
            persona_folder = Path("personas") / persona_id
            if not persona_folder.exists():
                await interaction.followup.send(
                    ResponseFormatter.error(
                        f"Persona folder not found: {persona_folder}"
                    ),
                    ephemeral=True,
                )
                return

            # Save image to persona folder
            image_path = persona_folder / save_filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # Force reload persona to regenerate appearance cache
            bot.agent_core.persona_loader.reload_persona(persona_id)

            # Get updated persona with new cached appearance
            updated_persona = bot.agent_core.persona_loader.get_persona(persona_id)

            if updated_persona and updated_persona.cached_appearance:
                await interaction.followup.send(
                    ResponseFormatter.success(
                        f"✅ Image saved to **{persona.name}** (`{persona_id}`)!\n\n"
                        f"**File:** `{save_filename}`\n"
                        f"**Location:** `{image_path}`\n\n"
                        f"**Generated appearance cache:**\n"
                        f"{updated_persona.cached_appearance[:500]}{'...' if len(updated_persona.cached_appearance) > 500 else ''}\n\n"
                        f"The appearance will be automatically injected into the system prompt."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    ResponseFormatter.warning(
                        f"✓ Image saved to `{image_path}`, but appearance generation failed.\n"
                        f"The image will be processed on next persona load."
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Failed to add image: {str(e)}"),
                ephemeral=True,
            )

    @persona_group.command(
        name="list_images",
        description="List all images in a persona folder",
    )
    @app_commands.describe(persona_id="The ID of the persona to check")
    async def list_persona_images(
        interaction: discord.Interaction,
        persona_id: str,
    ):
        """List all images in a persona folder."""
        from pathlib import Path

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

        # Build path to persona folder
        persona_folder = Path("personas") / persona_id
        if not persona_folder.exists():
            await interaction.response.send_message(
                ResponseFormatter.error(f"Persona folder not found: {persona_folder}"),
                ephemeral=True,
            )
            return

        # Find all image files
        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        images = [
            f
            for f in persona_folder.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not images:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    f"**{persona.name}** (`{persona_id}`) has no images.\n\n"
                    f"Use `/persona add_image` to add images for appearance generation."
                ),
                ephemeral=True,
            )
            return

        # Build response
        response = f"**Images for {persona.name}** (`{persona_id}`):\n\n"

        for img in sorted(images):
            size_kb = img.stat().st_size / 1024
            response += f"• `{img.name}` ({size_kb:.1f} KB)\n"

        response += f"\n**Total:** {len(images)} image(s)"

        # Show cached appearance status
        if persona.cached_appearance:
            response += f"\n\n✅ **Cached appearance:** Generated ({len(persona.cached_appearance)} chars)"
        else:
            response += f"\n\n⚠️ **Cached appearance:** Not yet generated"

        await interaction.response.send_message(response, ephemeral=True)

    @persona_group.command(
        name="remove_image",
        description="Remove an image from a persona folder",
    )
    @app_commands.describe(
        persona_id="The ID of the persona",
        filename="The image filename to remove",
    )
    async def remove_persona_image(
        interaction: discord.Interaction,
        persona_id: str,
        filename: str,
    ):
        """Remove an image from a persona folder and regenerate appearance."""
        from pathlib import Path
        import os

        # Verify persona exists
        persona = bot.agent_core.persona_loader.get_persona(persona_id)
        if not persona:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Persona '{persona_id}' not found."),
                ephemeral=True,
            )
            return

        # Build path to image
        persona_folder = Path("personas") / persona_id
        image_path = persona_folder / filename

        if not image_path.exists():
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Image '{filename}' not found in persona folder.\n"
                    f"Use `/persona list_images {persona_id}` to see available images."
                ),
                ephemeral=True,
            )
            return

        # Delete the image
        try:
            os.remove(image_path)

            # Force reload to regenerate appearance cache
            bot.agent_core.persona_loader.reload_persona(persona_id)

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Removed `{filename}` from **{persona.name}**\n\n"
                    f"Appearance cache has been regenerated from remaining images."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to remove image: {str(e)}"),
                ephemeral=True,
            )

    @persona_group.command(
        name="regenerate_appearance",
        description="Force regenerate appearance cache from persona images",
    )
    @app_commands.describe(persona_id="The ID of the persona to regenerate")
    async def regenerate_appearance(
        interaction: discord.Interaction,
        persona_id: str,
    ):
        """Force regenerate the appearance cache from images."""
        from pathlib import Path
        import sqlite3

        # Check if vision cache service is available
        if not hasattr(bot, "vision_cache_service") or bot.vision_cache_service is None:
            await interaction.response.send_message(
                ResponseFormatter.error("Vision cache service is not configured."),
                ephemeral=True,
            )
            return

        # Verify persona exists
        persona = bot.agent_core.persona_loader.get_persona(persona_id)
        if not persona:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Persona '{persona_id}' not found."),
                ephemeral=True,
            )
            return

        # Check if persona has images
        persona_folder = Path("personas") / persona_id
        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        images = [
            f
            for f in persona_folder.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not images:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    f"**{persona.name}** has no images.\n"
                    f"Use `/persona add_image` to add images first."
                ),
                ephemeral=True,
            )
            return

        # Defer response
        await interaction.response.defer(ephemeral=True)

        try:
            # Clear cached appearance from database to force regeneration
            if bot.agent_core.persona_loader.db_path:
                conn = sqlite3.connect(bot.agent_core.persona_loader.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM persona_appearances WHERE persona_id = ?",
                    (persona_id,),
                )
                conn.commit()
                conn.close()

            # Force reload persona - this will trigger appearance generation
            bot.agent_core.persona_loader.reload_persona(persona_id)

            # Get updated persona
            updated_persona = bot.agent_core.persona_loader.get_persona(persona_id)

            if updated_persona and updated_persona.cached_appearance:
                await interaction.followup.send(
                    ResponseFormatter.success(
                        f"✅ Regenerated appearance for **{persona.name}**\n\n"
                        f"**Processed {len(images)} image(s)**\n\n"
                        f"**New appearance:**\n"
                        f"{updated_persona.cached_appearance[:500]}{'...' if len(updated_persona.cached_appearance) > 500 else ''}"
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    ResponseFormatter.error(
                        f"Failed to regenerate appearance. Check vision service status."
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Error regenerating appearance: {str(e)}"),
                ephemeral=True,
            )

    # Register the persona group
    bot.tree.add_command(persona_group)

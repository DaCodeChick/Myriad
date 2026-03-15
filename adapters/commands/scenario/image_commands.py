"""
Scenario image management commands.

Handles adding, listing, removing, and regenerating appearance cache for scenario images.
"""

import os
import sqlite3
import discord
from discord import app_commands
from pathlib import Path
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_image_commands(
    bot: "MyriadDiscordBot", scenario_group: app_commands.Group
) -> None:
    """Register scenario image management commands."""

    @scenario_group.command(
        name="add_image",
        description="Add an image to a scenario folder (auto-generates appearance cache)",
    )
    @app_commands.describe(
        name="The name of the scenario to update",
        image="Scenario image attachment",
        filename="Optional filename (default: uses attachment name)",
    )
    async def add_scenario_image(
        interaction: discord.Interaction,
        name: str,
        image: discord.Attachment,
        filename: str = "",
    ):
        """Add an image to a scenario folder and trigger appearance regeneration."""
        # Check if vision service is available
        if (
            not hasattr(bot.agent_core.scenario_engine, "vision_service")
            or bot.agent_core.scenario_engine.vision_service is None
        ):
            await interaction.response.send_message(
                ResponseFormatter.error(
                    "Vision service is not configured. "
                    "Please set VISION_BASE_URL and VISION_MODEL in your environment."
                ),
                ephemeral=True,
            )
            return

        # Verify scenario exists
        scenario = bot.agent_core.scenario_engine.get_scenario(name)
        if not scenario:
            available = bot.agent_core.scenario_engine.list_all_scenarios()
            scenario_names = [s.name for s in available]
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Scenario '{name}' not found.\n"
                    f"Available scenarios: {', '.join(scenario_names[:10])}"
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

            # Build path to scenario folder
            scenario_folder = Path("scenarios") / name
            if not scenario_folder.exists():
                await interaction.followup.send(
                    ResponseFormatter.error(
                        f"Scenario folder not found: {scenario_folder}"
                    ),
                    ephemeral=True,
                )
                return

            # Save image to scenario folder
            image_path = scenario_folder / save_filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # Force reload scenario to regenerate appearance cache
            updated_scenario = bot.agent_core.scenario_engine.get_scenario(name)

            if updated_scenario and updated_scenario.cached_appearance:
                await interaction.followup.send(
                    ResponseFormatter.success(
                        f"✅ Image saved to **{scenario.name}**!\n\n"
                        f"**File:** `{save_filename}`\n"
                        f"**Location:** `{image_path}`\n\n"
                        f"**Generated appearance cache:**\n"
                        f"{updated_scenario.cached_appearance[:500]}{'...' if len(updated_scenario.cached_appearance) > 500 else ''}\n\n"
                        f"The appearance will be automatically injected into the context."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    ResponseFormatter.warning(
                        f"✓ Image saved to `{image_path}`, but appearance generation failed.\n"
                        f"The image will be processed on next scenario load."
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Failed to add image: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="list_images",
        description="List all images in a scenario folder",
    )
    @app_commands.describe(name="The name of the scenario to check")
    async def list_scenario_images(
        interaction: discord.Interaction,
        name: str,
    ):
        """List all images in a scenario folder."""
        # Verify scenario exists
        scenario = bot.agent_core.scenario_engine.get_scenario(name)
        if not scenario:
            available = bot.agent_core.scenario_engine.list_all_scenarios()
            scenario_names = [s.name for s in available]
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Scenario '{name}' not found.\n"
                    f"Available scenarios: {', '.join(scenario_names[:10])}"
                ),
                ephemeral=True,
            )
            return

        # Build path to scenario folder
        scenario_folder = Path("scenarios") / name
        if not scenario_folder.exists():
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Scenario folder not found: {scenario_folder}"
                ),
                ephemeral=True,
            )
            return

        # Find all image files
        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        images = [
            f
            for f in scenario_folder.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not images:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    f"**{scenario.name}** has no images.\n\n"
                    f"Use `/scenario add_image` to add images for appearance generation."
                ),
                ephemeral=True,
            )
            return

        # Build response
        response = f"**Images for {scenario.name}**:\n\n"

        for img in sorted(images):
            size_kb = img.stat().st_size / 1024
            response += f"• `{img.name}` ({size_kb:.1f} KB)\n"

        response += f"\n**Total:** {len(images)} image(s)"

        # Show cached appearance status
        if scenario.cached_appearance:
            response += f"\n\n✅ **Cached appearance:** Generated ({len(scenario.cached_appearance)} chars)"
        else:
            response += f"\n\n⚠️ **Cached appearance:** Not yet generated"

        await interaction.response.send_message(response, ephemeral=True)

    @scenario_group.command(
        name="remove_image",
        description="Remove an image from a scenario folder",
    )
    @app_commands.describe(
        name="The name of the scenario",
        filename="The image filename to remove",
    )
    async def remove_scenario_image(
        interaction: discord.Interaction,
        name: str,
        filename: str,
    ):
        """Remove an image from a scenario folder and regenerate appearance."""
        # Verify scenario exists
        scenario = bot.agent_core.scenario_engine.get_scenario(name)
        if not scenario:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Scenario '{name}' not found."),
                ephemeral=True,
            )
            return

        # Build path to image
        scenario_folder = Path("scenarios") / name
        image_path = scenario_folder / filename

        if not image_path.exists():
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Image '{filename}' not found in scenario folder.\n"
                    f"Use `/scenario list_images {name}` to see available images."
                ),
                ephemeral=True,
            )
            return

        # Delete the image
        try:
            os.remove(image_path)

            # Force reload to regenerate appearance cache by getting scenario again
            bot.agent_core.scenario_engine.get_scenario(name)

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Removed `{filename}` from **{scenario.name}**\n\n"
                    f"Appearance cache has been regenerated from remaining images."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to remove image: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="regenerate_appearance",
        description="Force regenerate appearance cache from scenario images",
    )
    @app_commands.describe(name="The name of the scenario to regenerate")
    async def regenerate_appearance(
        interaction: discord.Interaction,
        name: str,
    ):
        """Force regenerate the appearance cache from images."""
        # Check if vision service is available
        if (
            not hasattr(bot.agent_core.scenario_engine, "vision_service")
            or bot.agent_core.scenario_engine.vision_service is None
        ):
            await interaction.response.send_message(
                ResponseFormatter.error("Vision service is not configured."),
                ephemeral=True,
            )
            return

        # Verify scenario exists
        scenario = bot.agent_core.scenario_engine.get_scenario(name)
        if not scenario:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Scenario '{name}' not found."),
                ephemeral=True,
            )
            return

        # Check if scenario has images
        scenario_folder = Path("scenarios") / name
        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        images = [
            f
            for f in scenario_folder.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not images:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    f"**{scenario.name}** has no images.\n"
                    f"Use `/scenario add_image` to add images first."
                ),
                ephemeral=True,
            )
            return

        # Defer response
        await interaction.response.defer(ephemeral=True)

        try:
            # Clear cached appearance from database to force regeneration
            if bot.agent_core.scenario_engine.db_path:
                conn = sqlite3.connect(bot.agent_core.scenario_engine.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM scenario_appearances WHERE scenario_name = ?",
                    (name,),
                )
                conn.commit()
                conn.close()

            # Force reload scenario - this will trigger appearance generation
            updated_scenario = bot.agent_core.scenario_engine.get_scenario(name)

            if updated_scenario and updated_scenario.cached_appearance:
                await interaction.followup.send(
                    ResponseFormatter.success(
                        f"✅ Regenerated appearance for **{scenario.name}**\n\n"
                        f"**Processed {len(images)} image(s)**\n\n"
                        f"**New appearance:**\n"
                        f"{updated_scenario.cached_appearance[:500]}{'...' if len(updated_scenario.cached_appearance) > 500 else ''}"
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

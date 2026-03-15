"""
Scenario Engine (World Tree) commands for Discord.

Handles creation and management of hierarchical environmental contexts.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_scenario_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all scenario-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    # Scenario Management Commands
    scenario_group = app_commands.Group(
        name="scenario",
        description="World Tree - hierarchical environmental context management",
    )

    @scenario_group.command(
        name="create",
        description="Create a new scenario/location in the world tree",
    )
    @app_commands.describe(
        name="Unique name for this scenario (e.g., 'Zeal Palace', 'Schala's Room')",
        description="Detailed description of this location/scenario",
    )
    async def create_scenario(
        interaction: discord.Interaction, name: str, description: str
    ):
        """Create a new scenario."""
        try:
            scenario = bot.agent_core.scenario_engine.create_scenario(
                name=name, description=description
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Created scenario: **{scenario.name}**\n"
                    f"• Description: {description}\n\n"
                    f"Use `/scenario set_parent` to nest this inside another scenario."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to create scenario: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="set_parent",
        description="Nest a scenario inside another one (e.g., room inside building)",
    )
    @app_commands.describe(
        child_name="The scenario to nest (e.g., 'Schala's Room')",
        parent_name="The parent scenario (e.g., 'Zeal Palace')",
    )
    async def set_parent(
        interaction: discord.Interaction, child_name: str, parent_name: str
    ):
        """Set a scenario's parent, creating hierarchical nesting."""
        try:
            bot.agent_core.scenario_engine.set_parent(child_name, parent_name)

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Successfully nested **{child_name}** inside **{parent_name}**\n\n"
                    f"Use `/scenario look` to view the hierarchy."
                ),
                ephemeral=True,
            )
        except ValueError as e:
            await interaction.response.send_message(
                ResponseFormatter.error(str(e)), ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to set parent: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="enter",
        description="Enter a scenario (sets your active environmental context)",
    )
    @app_commands.describe(name="The name of the scenario to enter")
    async def enter_scenario(interaction: discord.Interaction, name: str):
        """Set the active scenario for the user."""
        user_id = str(interaction.user.id)

        try:
            scenario = bot.agent_core.scenario_engine.get_scenario(name)

            if not scenario:
                # List available scenarios
                scenarios = bot.agent_core.scenario_engine.list_all_scenarios()
                if scenarios:
                    scenario_list = ", ".join([f"'{s.name}'" for s in scenarios])
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Scenario '{name}' not found.\n"
                            f"Available scenarios: {scenario_list}"
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        ResponseFormatter.error(
                            f"Scenario '{name}' not found. No scenarios exist yet.\n"
                            f"Use `/scenario create` to create one."
                        ),
                        ephemeral=True,
                    )
                return

            # Set as active scenario
            bot.agent_core.scenario_engine.set_active_scenario(user_id, scenario.name)

            # Get the full hierarchy to show the user
            hierarchy = bot.agent_core.scenario_engine.get_scenario_hierarchy(
                scenario.name
            )

            # Build a visual representation of where they are
            location_path = " → ".join([s.name for s in hierarchy])

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Entered scenario: **{scenario.name}**\n\n"
                    f"**Full location path:**\n{location_path}\n\n"
                    f"The AI will now recognize this environmental context.\n"
                    f"Use `/scenario look` to see full details."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to enter scenario: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="exit",
        description="Exit the current scenario (clears environmental context)",
    )
    async def exit_scenario(interaction: discord.Interaction):
        """Clear the active scenario."""
        user_id = str(interaction.user.id)

        try:
            # Get current scenario before clearing
            current = bot.agent_core.scenario_engine.get_active_scenario(user_id)

            # Clear the active scenario
            bot.agent_core.scenario_engine.set_active_scenario(user_id, None)

            if current:
                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"Exited scenario: **{current.name}**\n"
                        f"You are now in undefined space."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    ResponseFormatter.warning("You weren't in any scenario."),
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to exit scenario: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="look",
        description="View the full hierarchy of your current environmental context",
    )
    async def look_scenario(interaction: discord.Interaction):
        """Show the current nested scenario tree."""
        user_id = str(interaction.user.id)

        try:
            active_scenario = bot.agent_core.scenario_engine.get_active_scenario(
                user_id
            )

            if not active_scenario:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "You're not in any scenario.\n"
                        "Use `/scenario enter <name>` to enter one, or `/scenario create` to make one."
                    ),
                    ephemeral=True,
                )
                return

            # Get the full hierarchy
            hierarchy = bot.agent_core.scenario_engine.get_scenario_hierarchy(
                active_scenario.name
            )

            # Build a rich display
            response = "**🌍 Current Environmental Context:**\n\n"

            for i, scenario in enumerate(hierarchy):
                indent = "  " * i
                arrow = "└─ " if i == len(hierarchy) - 1 else "├─ "
                active_marker = (
                    " 📍 **(YOU ARE HERE)**" if i == len(hierarchy) - 1 else ""
                )

                if i == 0:
                    level_icon = "🌐"  # World state
                elif i == len(hierarchy) - 1:
                    level_icon = "📍"  # Current location
                else:
                    level_icon = "🏛️"  # Macro location

                response += (
                    f"{indent}{arrow}{level_icon} **{scenario.name}**{active_marker}\n"
                )
                response += f"{indent}   _{scenario.description}_\n\n"

            response += "\nUse `/scenario exit` to leave this scenario."

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to display scenario: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="list",
        description="List all available scenarios in the world tree",
    )
    async def list_scenarios(interaction: discord.Interaction):
        """List all scenarios."""
        try:
            scenarios = bot.agent_core.scenario_engine.list_all_scenarios()

            if not scenarios:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        "No scenarios exist yet.\n"
                        "Use `/scenario create` to create your first scenario."
                    ),
                    ephemeral=True,
                )
                return

            # Group scenarios by whether they have parents or not
            root_scenarios = [s for s in scenarios if s.parent_id is None]
            nested_scenarios = [s for s in scenarios if s.parent_id is not None]

            response = "**📚 All Scenarios:**\n\n"

            if root_scenarios:
                response += "**Root Scenarios (no parent):**\n"
                for s in root_scenarios:
                    response += f"• **{s.name}** (ID: {s.id})\n"
                response += "\n"

            if nested_scenarios:
                response += "**Nested Scenarios (has parent):**\n"
                for s in nested_scenarios:
                    # Get parent name
                    parent = bot.agent_core.scenario_engine.get_scenario_by_id(
                        s.parent_id
                    )
                    parent_name = parent.name if parent else "Unknown"
                    response += (
                        f"• **{s.name}** → inside _{parent_name}_ (ID: {s.id})\n"
                    )

            response += f"\n**Total:** {len(scenarios)} scenario(s)"
            response += "\n\nUse `/scenario enter <name>` to enter a scenario."

            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to list scenarios: {str(e)}"),
                ephemeral=True,
            )

    @scenario_group.command(
        name="delete",
        description="Delete a scenario (children will become orphaned)",
    )
    @app_commands.describe(name="The name of the scenario to delete")
    async def delete_scenario(interaction: discord.Interaction, name: str):
        """Delete a scenario."""
        try:
            scenario = bot.agent_core.scenario_engine.get_scenario(name)

            if not scenario:
                await interaction.response.send_message(
                    ResponseFormatter.error(f"Scenario '{name}' not found."),
                    ephemeral=True,
                )
                return

            bot.agent_core.scenario_engine.delete_scenario(name)

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Deleted scenario: **{name}**\n"
                    f"Any child scenarios are now orphaned (parent_id set to NULL)."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to delete scenario: {str(e)}"),
                ephemeral=True,
            )

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
        import os
        from pathlib import Path

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
        from pathlib import Path

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
        from pathlib import Path
        import os

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
        from pathlib import Path
        import sqlite3

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

    # Register the scenario group
    bot.tree.add_command(scenario_group)

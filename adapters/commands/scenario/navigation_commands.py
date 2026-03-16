"""
Scenario navigation commands.

Handles entering, exiting, viewing, and listing scenarios.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter


def _get_roleplay_feature(bot):
    """Get roleplay feature from bot, or None if not enabled."""
    return bot.agent_core.features.get("roleplay")


if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_navigation_commands(
    bot: "MyriadDiscordBot", scenario_group: app_commands.Group
) -> None:
    """Register scenario navigation commands."""

    @scenario_group.command(
        name="enter",
        description="Enter a scenario (sets your active environmental context)",
    )
    @app_commands.describe(name="The name of the scenario to enter")
    async def enter_scenario(interaction: discord.Interaction, name: str):
        """Set the active scenario for the user."""
        user_id = str(interaction.user.id)

        try:
            scenario = _get_roleplay_feature(bot).scenario_engine.get_scenario(name)

            if not scenario:
                # List available scenarios
                scenarios = _get_roleplay_feature(bot).scenario_engine.list_all_scenarios()
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
            _get_roleplay_feature(bot).scenario_engine.set_active_scenario(user_id, scenario.name)

            # Get the full hierarchy to show the user
            hierarchy = _get_roleplay_feature(bot).scenario_engine.get_scenario_hierarchy(
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
            current = _get_roleplay_feature(bot).scenario_engine.get_active_scenario(user_id)

            # Clear the active scenario
            _get_roleplay_feature(bot).scenario_engine.set_active_scenario(user_id, None)

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
            active_scenario = _get_roleplay_feature(bot).scenario_engine.get_active_scenario(
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
            hierarchy = _get_roleplay_feature(bot).scenario_engine.get_scenario_hierarchy(
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
            scenarios = _get_roleplay_feature(bot).scenario_engine.list_all_scenarios()

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
                    parent = _get_roleplay_feature(bot).scenario_engine.get_scenario_by_id(
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

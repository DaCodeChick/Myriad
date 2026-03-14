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
                    f"• Description: {description}\n"
                    f"• ID: {scenario.id}\n\n"
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
            bot.agent_core.scenario_engine.set_active_scenario(user_id, scenario.id)

            # Get the full hierarchy to show the user
            hierarchy = bot.agent_core.scenario_engine.get_scenario_hierarchy(
                scenario.id
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
                active_scenario.id
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

    # Register the scenario group
    bot.tree.add_command(scenario_group)

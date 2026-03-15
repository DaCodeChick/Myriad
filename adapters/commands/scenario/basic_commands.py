"""
Basic scenario management commands.

Handles creation, hierarchy setup, and deletion of scenarios.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_basic_commands(
    bot: "MyriadDiscordBot", scenario_group: app_commands.Group
) -> None:
    """Register basic scenario management commands."""

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

"""
Scenario command registration coordinator.

Assembles all scenario commands into a unified command group.
"""

from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.scenario.basic_commands import register_basic_commands
from adapters.commands.scenario.navigation_commands import register_navigation_commands
from adapters.commands.scenario.image_commands import register_image_commands

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_scenario_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all scenario-related slash commands.

    Args:
        bot: The Discord bot instance
    """
    # Create the scenario command group
    scenario_group = app_commands.Group(
        name="scenario",
        description="World Tree - hierarchical environmental context management",
    )

    # Register all command modules
    register_basic_commands(bot, scenario_group)
    register_navigation_commands(bot, scenario_group)
    register_image_commands(bot, scenario_group)

    # Register the group with the bot
    bot.tree.add_command(scenario_group)

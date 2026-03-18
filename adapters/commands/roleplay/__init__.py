"""
Roleplay Commands - Discord interface for roleplay feature.

This package contains all roleplay-related commands organized by functionality:
- Persona management (ensemble, config, content)
- Limbic & degradation
- Lives & saves
- Masks & modes
- Narrative tools (retcon, dm)
- Notes & scenarios

RDSSC Phase 2: Commands reorganized by feature for better separation of concerns.
"""

from discord import app_commands
from typing import TYPE_CHECKING

# Import all command registration functions
from adapters.commands.roleplay.ensemble_commands import register_ensemble_commands
from adapters.commands.roleplay.config_commands import register_config_commands
from adapters.commands.roleplay.content_commands import register_content_commands
from adapters.commands.roleplay.lives_commands import register_lives_commands
from adapters.commands.roleplay.saves_commands import register_saves_commands
from adapters.commands.roleplay.mask_commands import register_mask_commands
from adapters.commands.roleplay.mode_commands import register_mode_commands
from adapters.commands.roleplay.narrative_commands import register_narrative_commands
from adapters.commands.roleplay.note_commands import register_note_commands
from adapters.commands.roleplay.degradation_commands import (
    register_degradation_commands,
)
from adapters.commands.roleplay.basic_commands import (
    register_basic_commands as register_scenario_basic,
)
from adapters.commands.roleplay.navigation_commands import register_navigation_commands
from adapters.commands.roleplay.image_commands import register_image_commands
from adapters.commands.roleplay.dm_commands import register_dm_commands
from adapters.commands.roleplay.awareness_commands import register_awareness_commands

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_roleplay_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all roleplay-related slash commands.

    Args:
        bot: The Discord bot instance
    """
    # Create persona command group
    persona_group = app_commands.Group(
        name="persona",
        description="Persona management - load, configure, and control AI characters",
    )

    # Persona commands (require persona_group)
    register_ensemble_commands(persona_group, bot)
    register_config_commands(persona_group, bot)
    register_content_commands(persona_group, bot)
    bot.tree.add_command(persona_group)

    # Lives & Saves
    register_lives_commands(bot)
    register_saves_commands(bot)

    # Masks & Modes
    register_mask_commands(bot)
    register_mode_commands(bot)

    # AI Awareness
    register_awareness_commands(bot)

    # Narrative tools
    register_narrative_commands(bot)
    register_dm_commands(bot)
    register_note_commands(bot)

    # Degradation (requires both bot and tree)
    register_degradation_commands(bot, bot.tree)

    # Scenario commands (World Tree) - use their own command group
    scenario_group = app_commands.Group(
        name="scenario",
        description="World Tree - hierarchical environmental context management",
    )
    register_scenario_basic(bot, scenario_group)
    register_navigation_commands(bot, scenario_group)
    register_image_commands(bot, scenario_group)
    bot.tree.add_command(scenario_group)


__all__ = ["register_roleplay_commands"]

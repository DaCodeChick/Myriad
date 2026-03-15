"""
Persona command module - coordinates all persona-related Discord commands.

This module was split from persona_commands.py during RDSSC Phase 1.

Components:
- basic_commands: swap, personas, whoami
- ensemble_commands: load, unload, clear, list_active
- content_commands: set_background, view_background, clear_background, add_image, list_images, remove_image, regenerate_appearance
- config_commands: set_narrator

Usage:
    from adapters.commands.persona import register_persona_commands
"""

from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.persona.basic_commands import register_basic_commands
from adapters.commands.persona.ensemble_commands import register_ensemble_commands
from adapters.commands.persona.content_commands import register_content_commands
from adapters.commands.persona.config_commands import register_config_commands

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_persona_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all persona-related slash commands.

    This coordinates the registration of:
    - Basic commands (top-level): swap, personas, whoami
    - Persona group commands: load, unload, clear, list_active, set_background,
      view_background, clear_background, add_image, list_images, remove_image,
      regenerate_appearance, set_narrator

    Args:
        bot: The Discord bot instance
    """
    # Register basic top-level commands (swap, personas, whoami)
    register_basic_commands(bot)

    # Create the persona group for advanced commands
    persona_group = app_commands.Group(
        name="persona", description="Advanced persona management commands"
    )

    # Register ensemble commands to the persona group
    register_ensemble_commands(persona_group, bot)

    # Register content management commands to the persona group
    register_content_commands(persona_group, bot)

    # Register configuration commands to the persona group
    register_config_commands(persona_group, bot)

    # Add the persona group to the bot's command tree
    bot.tree.add_command(persona_group)


__all__ = ["register_persona_commands"]

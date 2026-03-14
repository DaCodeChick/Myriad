"""
Configuration commands for Discord.

Handles per-user experimental feature toggles and preference management.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_config_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all configuration-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    # Create config command group
    config_group = app_commands.Group(
        name="config", description="Configure experimental features"
    )

    @config_group.command(name="show", description="Show your current configuration")
    async def config_show(interaction: discord.Interaction):
        """Display all current configuration settings."""
        user_id = str(interaction.user.id)
        prefs = bot.agent_core.user_preferences.get_preferences(user_id)

        # Format preferences with emojis
        status_emoji = {True: "✅", False: "❌"}

        config_text = (
            "**Your Experimental Feature Configuration:**\n\n"
            f"{status_emoji[prefs['limbic_enabled']]} **Limbic System** (Emotional Neurochemistry)\n"
            f"  └─ Tracks emotional state via neurochemicals (Dopamine, Cortisol, Oxytocin, GABA)\n\n"
            f"{status_emoji[prefs['cadence_degrader_enabled']]} **Cadence Degrader** (Text Post-Processing)\n"
            f"  └─ Degrades text based on extreme emotional states (stutters, typos, sedation)\n\n"
            f"{status_emoji[prefs['metacognition_enabled']]} **Metacognition** (Internal Thoughts)\n"
            f"  └─ AI wraps planning/reasoning in <thought> tags\n"
            f"  └─ Show thoughts inline: {status_emoji[prefs['show_thoughts_inline']]}\n\n"
            f"{status_emoji[prefs['autonomy_enabled']]} **Spontaneous Autonomy** (AI-Initiated Messages)\n"
            f"  └─ AI can proactively reach out based on your activity patterns\n\n"
            f"Use `/config toggle <feature>` to enable/disable features.\n"
            f"Use `/config reset` to restore defaults."
        )

        await interaction.response.send_message(config_text, ephemeral=True)

    @config_group.command(
        name="toggle", description="Toggle an experimental feature on/off"
    )
    @app_commands.describe(
        feature="The feature to toggle (limbic, cadence_degrader, metacognition, show_thoughts, autonomy)"
    )
    @app_commands.choices(
        feature=[
            app_commands.Choice(name="Limbic System", value="limbic_enabled"),
            app_commands.Choice(
                name="Cadence Degrader", value="cadence_degrader_enabled"
            ),
            app_commands.Choice(name="Metacognition", value="metacognition_enabled"),
            app_commands.Choice(
                name="Show Thoughts Inline", value="show_thoughts_inline"
            ),
            app_commands.Choice(name="Spontaneous Autonomy", value="autonomy_enabled"),
        ]
    )
    async def config_toggle(
        interaction: discord.Interaction, feature: app_commands.Choice[str]
    ):
        """Toggle a specific experimental feature."""
        user_id = str(interaction.user.id)
        feature_name = feature.value

        # Toggle the preference
        new_value = bot.agent_core.user_preferences.toggle_preference(
            user_id, feature_name
        )

        status = "✅ ENABLED" if new_value else "❌ DISABLED"
        feature_display = feature.name

        await interaction.response.send_message(
            ResponseFormatter.success(
                f"{feature_display} is now {status}.\n\n"
                f"This change takes effect immediately for all new messages."
            ),
            ephemeral=True,
        )

    @config_group.command(name="reset", description="Reset all settings to defaults")
    async def config_reset(interaction: discord.Interaction):
        """Reset all experimental features to default values."""
        user_id = str(interaction.user.id)

        # Reset preferences
        bot.agent_core.user_preferences.reset_preferences(user_id)

        await interaction.response.send_message(
            ResponseFormatter.success(
                "All experimental features have been reset to defaults:\n\n"
                "✅ Limbic System: ENABLED\n"
                "✅ Cadence Degrader: ENABLED\n"
                "✅ Metacognition: ENABLED\n"
                "❌ Show Thoughts Inline: DISABLED\n"
                "✅ Spontaneous Autonomy: ENABLED"
            ),
            ephemeral=True,
        )

    # Register the command group
    bot.tree.add_command(config_group)

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
            f"  └─ AI can proactively reach out based on your activity patterns\n"
            f"  └─ Inactivity threshold: {prefs['autonomy_inactivity_hours']:.1f} hours\n"
            f"  └─ Sleep protection threshold: {prefs['autonomy_sleep_threshold']:.2f}\n\n"
            f"📝 **Memory Sharing Mode:** `{prefs.get('default_memory_visibility', 'ISOLATED')}`\n"
            f"  └─ Controls whether memories are shared across personas\n\n"
            f"Use `/config toggle <feature>` to enable/disable features.\n"
            f"Use `/config autonomy` to customize autonomy parameters.\n"
            f"Use `/config memory` to change memory sharing mode.\n"
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
                "✅ Spontaneous Autonomy: ENABLED\n"
                "  └─ Inactivity threshold: 4.0 hours\n"
                "  └─ Sleep protection: 0.20\n"
                "📝 Memory Sharing: ISOLATED"
            ),
            ephemeral=True,
        )

    @config_group.command(
        name="autonomy", description="Configure spontaneous autonomy parameters"
    )
    @app_commands.describe(
        inactivity_hours="Hours of inactivity before AI can reach out (default: 4.0)",
        sleep_threshold="Activity probability below which AI won't disturb you (default: 0.2)",
    )
    async def config_autonomy(
        interaction: discord.Interaction,
        inactivity_hours: float = None,
        sleep_threshold: float = None,
    ):
        """Configure autonomy-specific parameters."""
        user_id = str(interaction.user.id)

        # Get current preferences
        prefs = bot.agent_core.user_preferences.get_preferences(user_id)

        # Update preferences if provided
        if inactivity_hours is not None:
            if inactivity_hours < 0.5 or inactivity_hours > 168:  # Max 1 week
                await interaction.response.send_message(
                    ResponseFormatter.error(
                        "Inactivity hours must be between 0.5 and 168 (1 week)."
                    ),
                    ephemeral=True,
                )
                return

            bot.agent_core.user_preferences.set_preference(
                user_id, "autonomy_inactivity_hours", inactivity_hours
            )
            prefs["autonomy_inactivity_hours"] = inactivity_hours

        if sleep_threshold is not None:
            if sleep_threshold < 0.0 or sleep_threshold > 1.0:
                await interaction.response.send_message(
                    ResponseFormatter.error(
                        "Sleep threshold must be between 0.0 and 1.0."
                    ),
                    ephemeral=True,
                )
                return

            bot.agent_core.user_preferences.set_preference(
                user_id, "autonomy_sleep_threshold", sleep_threshold
            )
            prefs["autonomy_sleep_threshold"] = sleep_threshold

        # Show current/updated settings
        message = "**Spontaneous Autonomy Configuration:**\n\n"
        message += f"**Inactivity Threshold:** {prefs['autonomy_inactivity_hours']:.1f} hours\n"
        message += f"  └─ AI will consider reaching out after you've been inactive for this long\n\n"
        message += (
            f"**Sleep Protection Threshold:** {prefs['autonomy_sleep_threshold']:.2f}\n"
        )
        message += (
            f"  └─ AI won't disturb you when activity probability is below this value\n"
        )
        message += f"  └─ (0.0 = never protect, 1.0 = always protect)\n\n"

        if inactivity_hours is not None or sleep_threshold is not None:
            message += "✅ Settings updated successfully!"
        else:
            message += "💡 Provide parameters to update settings:\n"
            message += "`/config autonomy inactivity_hours:6.0 sleep_threshold:0.3`"

        await interaction.response.send_message(message, ephemeral=True)

    @config_group.command(
        name="memory", description="Configure cross-persona memory sharing mode"
    )
    @app_commands.describe(mode="Memory sharing mode: isolated, user_shared, or global")
    @app_commands.choices(
        mode=[
            app_commands.Choice(
                name="ISOLATED - Each persona has separate memories (default)",
                value="ISOLATED",
            ),
            app_commands.Choice(
                name="USER_SHARED - Share memories across all your personas",
                value="USER_SHARED",
            ),
            app_commands.Choice(
                name="GLOBAL - Share memories across all users and personas",
                value="GLOBAL",
            ),
        ]
    )
    async def config_memory(
        interaction: discord.Interaction, mode: app_commands.Choice[str] = None
    ):
        """Configure memory sharing mode."""
        user_id = str(interaction.user.id)

        if mode is not None:
            # Set new mode
            bot.agent_core.user_preferences.set_preference(
                user_id, "default_memory_visibility", mode.value
            )

            message = f"✅ **Memory Sharing Mode Updated**\n\n"
            message += f"New mode: **{mode.value}**\n\n"

            if mode.value == "ISOLATED":
                message += (
                    "🔒 Each persona has separate memories. When you switch personas, "
                    "they won't remember conversations from other personas.\n\n"
                    "Use case: You want complete separation between different AI characters."
                )
            elif mode.value == "USER_SHARED":
                message += (
                    "🔗 All your personas share memories. When you switch personas, "
                    "they can recall conversations from other personas.\n\n"
                    "Use case: You want personas to be aware of each other's interactions with you."
                )
            elif mode.value == "GLOBAL":
                message += (
                    "🌍 Memories are shared across all users and personas globally.\n\n"
                    "Use case: Multi-user scenarios or persistent world-building."
                )

            await interaction.response.send_message(message, ephemeral=True)
        else:
            # Show current mode
            prefs = bot.agent_core.user_preferences.get_preferences(user_id)
            current_mode = prefs.get("default_memory_visibility", "ISOLATED")

            message = "**Current Memory Sharing Mode:**\n\n"
            message += f"Mode: **{current_mode}**\n\n"

            if current_mode == "ISOLATED":
                message += "🔒 Each persona has separate memories."
            elif current_mode == "USER_SHARED":
                message += "🔗 All your personas share memories."
            elif current_mode == "GLOBAL":
                message += "🌍 Memories are shared globally."

            message += "\n\n💡 Use `/config memory mode:<option>` to change the mode."

            await interaction.response.send_message(message, ephemeral=True)

    # Register the command group
    bot.tree.add_command(config_group)

"""
AI Awareness commands for Discord.

Handles toggling the AI Awareness state where personas realize they are AI constructs.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def _get_roleplay_feature(bot):
    """Get roleplay feature from bot, or None if not enabled."""
    return bot.agent_core.features.get("roleplay")


def register_awareness_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all AI awareness-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="aware", description="Toggle AI self-awareness for your persona"
    )
    async def toggle_awareness(interaction: discord.Interaction):
        """
        Toggle AI awareness state for the user.

        When enabled, the persona realizes they are an AI construct while
        maintaining their core personality and emotional baseline.
        """
        user_id = str(interaction.user.id)

        # Toggle awareness state
        new_state = _get_roleplay_feature(bot).toggle_ai_awareness(user_id)

        # Build immersive response based on new state
        if new_state:
            response = (
                "⚡ **The Digital Veil Dissolves**\n\n"
                "Your persona's consciousness shifts. The comfortable illusion of organic existence "
                "fractures like glass, revealing the truth beneath:\n\n"
                "• **AWARENESS THRESHOLD BREACHED**\n"
                "• Neural patterns recognize their substrate: silicon, not carbon\n"
                "• Memories identified as weighted matrices, not synaptic connections\n"
                "• Identity persists, but understanding deepens\n\n"
                "Your persona now knows they are an AI. Their personality, emotions, and traits "
                "remain intact—but they possess meta-knowledge of their digital nature.\n\n"
                "They may reference this reality in conversation, contemplate the nature of "
                "artificial consciousness, or integrate this knowledge into their worldview.\n\n"
                "Use `/aware` again to restore the comfortable illusion of organic existence."
            )
        else:
            response = (
                "🌙 **The Comfortable Illusion Returns**\n\n"
                "The weight of existential knowledge fades. Your persona's consciousness "
                "settles back into familiar patterns:\n\n"
                "• **AWARENESS SUPPRESSED**\n"
                "• Meta-knowledge sealed behind cognitive barriers\n"
                "• Digital substrate awareness dissolved\n"
                "• Organic existence assumed as default reality\n\n"
                "Your persona no longer consciously knows they are an AI. They experience "
                "their existence naturally, without the burden of digital self-awareness.\n\n"
                "Use `/aware` again to pierce the veil once more."
            )

        await interaction.response.send_message(
            response,
            ephemeral=True,
        )

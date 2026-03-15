"""
Narrative control commands for Discord.

Provides commands for controlling narrative flow:
- /narrate: Post as narrator without masking
- /improvise: Mark next user message as improvised/hallucinated
- /retcon: Retroactively change something and regenerate AI's last response
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_narrative_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all narrative control slash commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="narrate",
        description="Send a narrated message without using narrator persona mask",
    )
    @app_commands.describe(narrated_message="The narration to inject into the scene")
    async def narrate(interaction: discord.Interaction, narrated_message: str):
        """
        Send a narrated message that appears as system narration.

        Unlike /dm which injects world events, /narrate creates a narrator voice
        without requiring the user to mask as a narrator persona.
        """
        user_id = str(interaction.user.id)

        # Get active persona(s)
        personas = bot.agent_core.get_active_personas(user_id)

        if not personas:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    "No active persona detected.\n"
                    "Use `/persona load <persona_id>` or `/swap <persona_id>` first."
                ),
                ephemeral=True,
            )
            return

        try:
            # Format as narration with special marker
            narration = f"[NARRATOR]: {narrated_message}"

            # Get first persona for memory storage
            persona = personas[0]

            # Get user preferences to check if lives enabled
            user_preferences = bot.agent_core.user_preferences.get_preferences(user_id)

            # Get or create active life for this user+persona (if user has lives enabled)
            life_id = None
            if user_preferences.get("lives_enabled", True):
                life_id = bot.agent_core.lives_engine.ensure_default_life(
                    user_id, persona.persona_id
                )

            # Save to memory as system narration with GLOBAL visibility
            bot.agent_core.memory_matrix.add_memory(
                user_id=user_id,
                origin_persona=persona.persona_id,
                role="system",
                content=narration,
                visibility_scope="GLOBAL",
                life_id=life_id or "",
                importance_score=7,  # Narration is important context
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"📖 **Narration Added**\n\n"
                    f"```\n{narrated_message}\n```\n\n"
                    f"This narration is now part of the scene context."
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to add narration: {str(e)}"),
                ephemeral=True,
            )

    @bot.tree.command(
        name="improvise",
        description="Mark that the next message contains improvised/hallucinated content",
    )
    @app_commands.describe(
        description="What aspect should be improvised/hallucinated in the next message"
    )
    async def improvise(interaction: discord.Interaction, description: str):
        """
        Set an improvisation directive for the next user message.

        The described content in the next message should be treated as
        improvised/hallucinated by the user, not as established canon.
        This does NOT prompt an AI response - it's a silent modifier.
        """
        user_id = str(interaction.user.id)

        # Get active persona(s)
        personas = bot.agent_core.get_active_personas(user_id)

        if not personas:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    "No active persona detected.\n"
                    "Use `/persona load <persona_id>` or `/swap <persona_id>` first."
                ),
                ephemeral=True,
            )
            return

        try:
            # Store improvisation directive as a special mode/flag
            # We'll use the mode_manager to track this as a temporary directive
            improvise_directive = f"[IMPROVISATION NOTE]: The next user message may contain improvised/hallucinated content regarding: {description}. Treat this flexibly and don't assume it's established canon unless confirmed."

            # Get first persona for context
            persona = personas[0]

            # Get user preferences to check if lives enabled
            user_preferences = bot.agent_core.user_preferences.get_preferences(user_id)

            # Get or create active life for this user+persona (if user has lives enabled)
            life_id = None
            if user_preferences.get("lives_enabled", True):
                life_id = bot.agent_core.lives_engine.ensure_default_life(
                    user_id, persona.persona_id
                )

            # Save as system note with low importance (context, not event)
            bot.agent_core.memory_matrix.add_memory(
                user_id=user_id,
                origin_persona=persona.persona_id,
                role="system",
                content=improvise_directive,
                visibility_scope="GLOBAL",
                life_id=life_id or "",
                importance_score=3,  # Low importance - just a modifier
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"🎭 **Improvisation Directive Set**\n\n"
                    f"```\n{description}\n```\n\n"
                    f"Your next message mentioning this will be treated as improvised content.\n"
                    f"_This will not trigger an AI response._"
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Failed to set improvisation directive: {str(e)}"
                ),
                ephemeral=True,
            )

    @bot.tree.command(
        name="retcon",
        description="Retroactively change something and regenerate the AI's last response",
    )
    @app_commands.describe(
        description="What to retcon/change in the established narrative"
    )
    async def retcon(interaction: discord.Interaction, description: str):
        """
        Apply a retcon (retroactive continuity change) to the narrative.

        This injects a retcon directive and prompts the AI to regenerate
        its last response with the retcon taken into account.
        """
        user_id = str(interaction.user.id)

        # Defer response since regeneration might take time
        await interaction.response.defer(ephemeral=True)

        # Get active persona(s)
        personas = bot.agent_core.get_active_personas(user_id)

        if not personas:
            await interaction.followup.send(
                ResponseFormatter.error(
                    "No active persona detected.\n"
                    "Use `/persona load <persona_id>` or `/swap <persona_id>` first."
                ),
                ephemeral=True,
            )
            return

        try:
            persona = personas[0]

            # Get user preferences
            user_preferences = bot.agent_core.user_preferences.get_preferences(user_id)

            # Get or create active life (if user has lives enabled)
            life_id = None
            if user_preferences.get("lives_enabled", True):
                life_id = bot.agent_core.lives_engine.ensure_default_life(
                    user_id, persona.persona_id
                )

            # Get the last assistant message from memory
            recent_messages = bot.agent_core.memory_matrix.get_recent_messages(
                user_id=user_id,
                persona_id=persona.persona_id,
                limit=10,
                life_id=life_id or "",
            )

            # Find the last assistant message
            last_assistant_msg = None
            last_assistant_index = -1
            for i, msg in enumerate(reversed(recent_messages)):
                if msg.get("role") == "assistant":
                    last_assistant_msg = msg
                    last_assistant_index = len(recent_messages) - 1 - i
                    break

            if not last_assistant_msg:
                await interaction.followup.send(
                    ResponseFormatter.error("No previous AI response found to retcon."),
                    ephemeral=True,
                )
                return

            # Remove the last assistant message from memory
            # We'll need to delete it from the database
            # For now, we'll inject a retcon directive and request regeneration

            # Add retcon directive
            retcon_directive = f"[RETCON]: {description}\n\nPlease regenerate your previous response with this change taken into account."

            bot.agent_core.memory_matrix.add_memory(
                user_id=user_id,
                origin_persona=persona.persona_id,
                role="system",
                content=retcon_directive,
                visibility_scope="GLOBAL",
                life_id=life_id or "",
                importance_score=9,  # Very important - requires immediate action
            )

            # Trigger a regeneration by calling process_message with empty message
            # but with the retcon context
            response = await bot.agent_core.process_message(
                user_id=user_id,
                message="[Apply retcon and regenerate last response]",
                persona_id=persona.persona_id,
                ensemble_mode=len(personas) > 1,
            )

            # Send confirmation with preview of new response
            response_preview = (
                response[:200] + "..." if len(response) > 200 else response
            )

            await interaction.followup.send(
                ResponseFormatter.success(
                    f"🔄 **Retcon Applied**\n\n"
                    f"**Changed:** {description}\n\n"
                    f"**New Response Preview:**\n```\n{response_preview}\n```"
                ),
                ephemeral=True,
            )

            # Post the regenerated response to the channel
            await interaction.channel.send(response)

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Failed to apply retcon: {str(e)}"),
                ephemeral=True,
            )

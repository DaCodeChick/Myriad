"""
Dungeon Master commands for Discord.

Allows users to inject world events as a DM, with the active persona responding
in first-person to prevent perspective bleed.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_dm_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all Dungeon Master-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="dm",
        description="Send a Dungeon Master prompt - character responds in first-person",
    )
    @app_commands.describe(
        prompt="The DM scene/event (environmental descriptions, events, NPC actions, etc.)"
    )
    async def dm_narrate(interaction: discord.Interaction, prompt: str):
        """
        Inject a DM prompt with First-Person Anchor to prevent perspective bleed.

        The active persona will respond IN CHARACTER (first-person) to the DM's
        scene description, rather than narrating in third-person.
        """
        user_id = str(interaction.user.id)

        # Defer response since this will generate AI response
        await interaction.response.defer(ephemeral=False)

        try:
            # Get active persona
            personas = bot.agent_core.get_active_personas(user_id)
            if not personas:
                await interaction.followup.send(
                    ResponseFormatter.error(
                        "No active persona. Use `/swap <persona_id>` first."
                    ),
                    ephemeral=True,
                )
                return

            persona = personas[0]

            # Get user preferences
            user_preferences = bot.agent_core.user_preferences.get_preferences(user_id)

            # Get or create active life (if user has lives enabled)
            life_id = None
            if user_preferences.get("lives_enabled", True):
                life_id = bot.agent_core.lives_engine.ensure_default_life(
                    user_id, persona.persona_id
                )

            # Build DM message with First-Person Anchor directive
            # This prevents perspective bleed by forcing first-person response
            dm_message_with_anchor = (
                f"[Dungeon Master]: {prompt}\n\n"
                f"[System Directive]: Reply exclusively in character as {persona.name}. "
                f"You are {persona.name}. Describe YOUR internal thoughts, YOUR physical actions, "
                f"and speak YOUR dialogue in direct response to the Dungeon Master's scenario. "
                f"Do NOT narrate the story from a third-person perspective. Do NOT refer to "
                f"{persona.name} by name as if you are an outside observer. You ARE {persona.name}. "
                f"Respond in first-person only."
            )

            # Save the DM prompt as a system message (with anchor directive included)
            # This ensures it's part of the permanent conversation history
            bot.agent_core.memory_matrix.add_memory(
                user_id=user_id,
                origin_persona=persona.persona_id,
                role="system",
                content=dm_message_with_anchor,
                visibility_scope="GLOBAL",
                life_id=life_id or "",
                importance_score=7,
            )

            # Generate character's response to the DM prompt
            # The First-Person Anchor directive will be in the context
            response = bot.agent_core.process_message(
                user_id=user_id,
                message="[Respond to the Dungeon Master's prompt above in character]",
                memory_visibility="GLOBAL",
            )

            if not response:
                await interaction.followup.send(
                    ResponseFormatter.error(
                        "Failed to generate response. Check that you have an active persona."
                    ),
                    ephemeral=True,
                )
                return

            # Send the character's first-person response to the channel
            await interaction.followup.send(response)

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Failed to process DM prompt: {str(e)}"),
                ephemeral=True,
            )

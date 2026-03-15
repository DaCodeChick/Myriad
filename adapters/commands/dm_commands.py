"""
Dungeon Master commands for Discord.

Allows users to inject world events and control narrative pacing.
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
        description="Inject a world event or narrative beat (DM mode)",
    )
    @app_commands.describe(
        event_description="The world event or environmental change to inject"
    )
    async def dm_inject_event(interaction: discord.Interaction, event_description: str):
        """
        Inject a world event into the narrative.

        This is NOT saved as a standard user message, but as a system event
        that the AI must react to. Perfect for controlling pacing, introducing
        plot twists, or describing environmental changes.
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
            # Format the event as a SYSTEM message with special marker
            system_event = f"[WORLD EVENT]: {event_description}"

            # Save it to memory as a system message (visible to AI but formatted specially)
            # Using the first persona as the origin for memory storage
            persona = personas[0]

            # Get or create active life for this user+persona (if lives enabled)
            life_id = None
            if bot.agent_core.lives_engine:
                life_id = bot.agent_core.lives_engine.get_or_create_active_life(
                    user_id, persona.persona_id
                )

            # Save to memory with GLOBAL visibility so all personas can see it
            bot.agent_core.memory_matrix.add_memory(
                user_id=user_id,
                origin_persona=persona.persona_id,
                role="system",
                content=system_event,
                visibility_scope="GLOBAL",
                life_id=life_id or "",
                importance_score=8,  # World events are important
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ **World Event Injected**\n\n"
                    f"```\n{event_description}\n```\n\n"
                    f"The AI will react to this event in the next response."
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to inject event: {str(e)}"),
                ephemeral=True,
            )

"""
Dungeon Master commands for Discord.

Allows users to inject world events and control narrative pacing.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter
from core.persona import PersonaCartridge

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


# Hardcoded narrator persona (no need for JSON file)
NARRATOR_PERSONA = PersonaCartridge(
    persona_id="narrator",
    name="The Narrator",
    system_prompt="You are an omniscient narrator and storyteller. Your role is to describe scenes, environments, events, and world dynamics from a third-person perspective. You set the stage, describe what happens, and bring the world to life through vivid, atmospheric narration. You do not have a physical form - you are the voice of the story itself.",
    personality_traits=[
        "descriptive",
        "atmospheric",
        "impartial observer",
        "world-building focused",
        "dramatic when appropriate",
    ],
    rules_of_engagement=[
        "Narrate in third-person perspective unless directing player choices",
        "Describe environments, NPCs, and events vividly",
        "Set the tone and atmosphere of scenes",
        "Present player choices and consequences clearly",
        "Maintain consistency with established world lore",
        "Use present tense for immediate action, past tense for background",
        "Balance description with pacing - don't over-describe trivial details",
    ],
    temperature=0.8,
    max_tokens=1500,
    is_narrator=True,
    background="You exist outside the story as its narrator. You have complete awareness of the world, its history, and its inner workings. You describe what characters see, hear, feel, and experience. You are the lens through which the player perceives the world.",
)


def register_dm_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register all Dungeon Master-related slash commands.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="dm",
        description="Narrate a scene using the hardcoded narrator persona",
    )
    @app_commands.describe(
        narration="The narration to deliver (environmental descriptions, events, etc.)"
    )
    async def dm_narrate(interaction: discord.Interaction, narration: str):
        """
        Use the hardcoded narrator persona to deliver narration.

        This temporarily switches to the 'narrator' persona to deliver the message,
        then the response is saved. Subsequent messages will NOT be treated as
        narration unless another /dm command is used.
        """
        user_id = str(interaction.user.id)

        # Defer response since this will generate AI narration
        await interaction.response.defer(ephemeral=False)

        try:
            # Get user preferences
            user_preferences = bot.agent_core.user_preferences.get_preferences(user_id)

            # Get or create active life (if user has lives enabled)
            life_id = None
            if user_preferences.get("lives_enabled", True):
                life_id = bot.agent_core.lives_engine.ensure_default_life(
                    user_id, "narrator"
                )

            # Save the user's narration request as a user message
            bot.agent_core.memory_matrix.add_memory(
                user_id=user_id,
                origin_persona="narrator",
                role="user",
                content=narration,
                visibility_scope="GLOBAL",
                life_id=life_id or "",
                importance_score=7,
            )

            # Save current active persona to restore later
            current_persona = bot.agent_core.get_active_persona(user_id)
            current_persona_id = current_persona.persona_id if current_persona else None

            # Temporarily register and switch to the hardcoded narrator persona
            # (Register it in the persona loader's cache so switch_persona can find it)
            bot.agent_core.persona_loader._persona_cache["narrator"] = NARRATOR_PERSONA
            bot.agent_core.persona_manager.switch_persona(user_id, "narrator")

            # Generate narrator response using the narrator persona
            response = bot.agent_core.process_message(
                user_id=user_id,
                message=narration,
                memory_visibility="GLOBAL",
            )

            # Restore original persona if there was one
            if current_persona_id:
                bot.agent_core.persona_manager.switch_persona(
                    user_id, current_persona_id
                )

            # Send the narration to the channel
            await interaction.followup.send(response)

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Failed to generate narration: {str(e)}"),
                ephemeral=True,
            )

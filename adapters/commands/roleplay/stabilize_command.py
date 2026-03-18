"""
Stabilize command for Discord.

Forces an emotional reset by injecting a stabilization note that overrides
the recent high-intensity conversation context to break affective death spirals.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_stabilize_command(bot: "MyriadDiscordBot") -> None:
    """
    Register the /stabilize command.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="stabilize",
        description="Force emotional reset - breaks AI out of affective death spirals",
    )
    @app_commands.describe(
        summary="Brief summary of what just happened (e.g., 'We just had a massive argument and are cooling off')"
    )
    async def stabilize(interaction: discord.Interaction, summary: str):
        """
        Inject a stabilization note that overrides recent emotional context.

        This command helps break the AI out of affective death spirals where the
        context window is saturated with extreme emotion (rage, panic, arousal, etc.)
        by injecting a reset directive into the session notes.
        """
        # Defer immediately
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)

        # Get active persona
        personas = bot.agent_core.get_active_personas(user_id)
        if not personas:
            await interaction.followup.send(
                "❌ **No active persona.** Use `/persona swap <persona_id>` first.",
                ephemeral=True,
            )
            return

        persona = personas[0]

        try:
            # Create a stabilization directive that will be injected into the context
            stabilization_note = (
                f"[EMOTIONAL STABILIZATION OVERRIDE]\n\n"
                f"Context Summary: {summary}\n\n"
                f"DIRECTIVE: The intense emotional scene has concluded. You MUST now simulate the natural "
                f"physiological and psychological aftermath. Actively de-escalate your emotional state, "
                f"acknowledge physical/mental exhaustion from the intensity, and return to a calmer baseline. "
                f"The context window's repetition bias must be broken. This is a forced emotional reset."
            )

            # Inject into session notes with short TTL (5 turns to guide the transition)
            bot.agent_core.session_notes.set_note(
                user_id=user_id,
                note_text=stabilization_note,
                ttl_turns=5,
            )

            await interaction.followup.send(
                f"✅ **Emotional Stabilization Active**\n\n"
                f"**Summary:** {summary}\n\n"
                f"A stabilization directive has been injected into the AI's context. "
                f"The next response will include instructions to:\n"
                f"• Acknowledge the intense scene has concluded\n"
                f"• Simulate natural emotional/physical exhaustion\n"
                f"• De-escalate to a calmer baseline\n"
                f"• Break the context loop\n\n"
                f"**Duration:** 5 conversation turns (auto-expires)\n\n"
                f"This should force the AI out of the affective death spiral. "
                f"Use `/note clear` to remove early if needed.",
                ephemeral=True,
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ **Stabilization failed:** {str(e)}\n\n"
                f"The emotional reset could not be completed. Please try again.",
                ephemeral=True,
            )

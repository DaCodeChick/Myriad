"""
Ensemble persona commands - load, unload, clear, list_active.

Handles multi-persona "Ensemble Mode" where multiple AI personas can be active simultaneously.

Part of RDSSC Phase 1 refactoring - split from persona_commands.py.
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


def register_ensemble_commands(
    persona_group: app_commands.Group, bot: "MyriadDiscordBot"
) -> None:
    """
    Register ensemble persona commands (load, unload, clear, list_active).

    Args:
        persona_group: The persona command group to add commands to
        bot: The Discord bot instance
    """

    @persona_group.command(
        name="load",
        description="Load a persona into the ensemble (adds to active personas)",
    )
    @app_commands.describe(persona_id="The ID of the persona to load")
    async def load_persona(interaction: discord.Interaction, persona_id: str):
        """Load a persona into the ensemble."""
        user_id = str(interaction.user.id)

        # Check if roleplay feature is enabled
        roleplay = _get_roleplay_feature(bot)
        if not roleplay or not roleplay.persona_loader:
            await interaction.response.send_message(
                ResponseFormatter.error("Roleplay feature is not enabled."),
                ephemeral=True,
            )
            return

        # Verify persona exists
        persona = roleplay.persona_loader.get_persona(persona_id)
        if not persona:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available[:10])}"
                ),
                ephemeral=True,
            )
            return

        # Add to ensemble
        success = bot.agent_core.add_active_persona(user_id, persona_id)

        if success:
            # Get all active personas
            active_personas = bot.agent_core.get_active_personas(user_id)
            ensemble_status = (
                f"\n\n**Ensemble Mode Active** ({len(active_personas)} personas loaded)"
                if len(active_personas) > 1
                else ""
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Loaded persona: **{persona.name}** (`{persona_id}`){ensemble_status}"
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning(f"Persona '{persona_id}' is already loaded."),
                ephemeral=True,
            )

    @persona_group.command(
        name="swap",
        description="Switch to a single persona (clears ensemble and loads one persona)",
    )
    @app_commands.describe(persona_id="The ID of the persona to switch to")
    async def swap_persona(interaction: discord.Interaction, persona_id: str):
        """Switch the user's active persona."""
        print(
            f"[DEBUG] /persona swap called: persona_id={persona_id}, user={interaction.user.id}",
            flush=True,
        )
        try:
            # Defer immediately to prevent timeout
            print(f"[DEBUG] Deferring interaction...", flush=True)
            await interaction.response.defer(ephemeral=True)
            print(f"[DEBUG] Interaction deferred", flush=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer (Discord API latency)
            # This is a transient error - user should try again
            print(f"[DEBUG] Interaction expired (NotFound)", flush=True)
            return

        user_id = str(interaction.user.id)
        print(
            f"[DEBUG] Calling switch_persona for user_id={user_id}, persona_id={persona_id}",
            flush=True,
        )

        try:
            # Attempt to switch persona
            success = bot.agent_core.switch_persona(user_id, persona_id)
            print(f"[DEBUG] switch_persona returned: {success}", flush=True)

            if success:
                persona = bot.agent_core.get_active_persona(user_id)
                print(
                    f"[DEBUG] Got active persona: {persona.name if persona else None}",
                    flush=True,
                )
                if persona:  # Type guard to satisfy type checker
                    await interaction.followup.send(
                        ResponseFormatter.success(
                            f"Switched to persona: **{persona.name}** (`{persona_id}`)"
                        ),
                        ephemeral=True,
                    )
                    print(f"[DEBUG] Sent success message", flush=True)
            else:
                print(f"[DEBUG] switch_persona failed, sending error", flush=True)
                available = bot.agent_core.list_personas()
                await interaction.followup.send(
                    ResponseFormatter.error(
                        f"Persona '{persona_id}' not found.\n"
                        f"Available personas: {', '.join(available[:10])}"
                    ),
                    ephemeral=True,
                )
                print(f"[DEBUG] Sent error message", flush=True)
        except Exception as e:
            print(f"[ERROR] Exception in swap_persona: {e}", flush=True)
            import traceback

            traceback.print_exc()
            try:
                await interaction.followup.send(
                    ResponseFormatter.error(f"Error switching persona: {str(e)}"),
                    ephemeral=True,
                )
            except Exception as followup_error:
                print(
                    f"[ERROR] Failed to send error message: {followup_error}",
                    flush=True,
                )

    @persona_group.command(
        name="unload",
        description="Unload a specific persona from the ensemble",
    )
    @app_commands.describe(persona_id="The ID of the persona to unload")
    async def unload_persona(interaction: discord.Interaction, persona_id: str):
        """Remove a persona from the ensemble."""
        user_id = str(interaction.user.id)

        success = bot.agent_core.remove_active_persona(user_id, persona_id)

        if success:
            active_personas = bot.agent_core.get_active_personas(user_id)
            remaining_status = (
                f"\n\n**{len(active_personas)} persona(s) remaining**"
                if active_personas
                else "\n\n**No personas active**"
            )

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Unloaded persona: `{persona_id}`{remaining_status}"
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning(f"Persona '{persona_id}' was not loaded."),
                ephemeral=True,
            )

    @persona_group.command(
        name="clear",
        description="Clear all active personas from the ensemble",
    )
    async def clear_personas(interaction: discord.Interaction):
        """Clear all active personas."""
        user_id = str(interaction.user.id)

        # Get count before clearing
        active_personas = bot.agent_core.get_active_personas(user_id)
        count = len(active_personas)

        bot.agent_core.clear_active_personas(user_id)

        if count > 0:
            await interaction.response.send_message(
                ResponseFormatter.success(f"Cleared {count} persona(s) from ensemble."),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.warning("No personas were active."),
                ephemeral=True,
            )

    @persona_group.command(
        name="list_active",
        description="Show all currently loaded personas in the ensemble",
    )
    async def list_active_personas(interaction: discord.Interaction):
        """List all active personas in the ensemble."""
        user_id = str(interaction.user.id)

        active_personas = bot.agent_core.get_active_personas(user_id)

        if not active_personas:
            await interaction.response.send_message(
                ResponseFormatter.warning(
                    "No personas are currently active.\n\n"
                    "Use `/persona load <persona_id>` to load one, or\n"
                    "Use `/swap <persona_id>` to switch to a single persona."
                ),
                ephemeral=True,
            )
            return

        # Build response
        response = "**Active Personas:**\n\n"

        for persona in active_personas:
            # Check if narrator
            if persona.is_narrator:
                response += (
                    f"• **{persona.name}** (`{persona.persona_id}`) 🎲 **[NARRATOR]**\n"
                    f"  Role: Omniscient environmental narrator (no physical body)\n\n"
                )
            else:
                traits = (
                    ", ".join(persona.personality_traits[:3])
                    if persona.personality_traits
                    else "None"
                )
                bg_indicator = " 📖" if persona.background else ""
                img_indicator = " 🖼️" if persona.cached_appearance else ""

                response += (
                    f"• **{persona.name}** (`{persona.persona_id}`){bg_indicator}{img_indicator}\n"
                    f"  Traits: {traits}\n\n"
                )

        if len(active_personas) > 1:
            response += (
                f"**🎭 Ensemble Mode Active** ({len(active_personas)} personas)\n"
            )
            response += "The AI is controlling multiple characters as Dungeon Master/Narrator.\n\n"

        response += "📖 = Has background lore\n"
        response += "🖼️ = Has appearance images\n"
        response += "🎲 = Narrator (no physical body)"

        await interaction.response.send_message(response, ephemeral=True)

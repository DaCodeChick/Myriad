"""
Basic persona commands - swap, personas, whoami.

Handles fundamental persona operations like switching, listing, and viewing active persona status.

Part of RDSSC Phase 1 refactoring - split from persona_commands.py.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_basic_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register basic persona commands (swap, personas, whoami).

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(name="swap", description="Switch to a different persona")
    @app_commands.describe(persona_id="The ID of the persona to switch to")
    async def swap_persona(interaction: discord.Interaction, persona_id: str):
        """Switch the user's active persona."""
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer (Discord API latency)
            # This is a transient error - user should try again
            return

        user_id = str(interaction.user.id)

        # Attempt to switch persona
        success = bot.agent_core.switch_persona(user_id, persona_id)

        if success:
            persona = bot.agent_core.get_active_persona(user_id)
            if persona:  # Type guard to satisfy type checker
                await interaction.followup.send(
                    ResponseFormatter.success(
                        f"Switched to persona: **{persona.name}** (`{persona_id}`)"
                    ),
                    ephemeral=True,
                )
        else:
            available = bot.agent_core.list_personas()
            await interaction.followup.send(
                ResponseFormatter.error(
                    f"Persona '{persona_id}' not found.\n"
                    f"Available personas: {', '.join(available)}"
                ),
                ephemeral=True,
            )

    @bot.tree.command(name="personas", description="List all available personas")
    async def list_personas_cmd(interaction: discord.Interaction):
        """List all available persona cartridges."""
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer (Discord API latency)
            return

        personas = bot.agent_core.list_personas()

        if personas:
            persona_list = "\n".join([f"• `{p}`" for p in personas])
            await interaction.followup.send(
                f"**Available Personas:**\n{persona_list}\n\n"
                f"Use `/swap <persona_id>` to switch.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                ResponseFormatter.warning(
                    "No personas found in the `personas/` directory."
                ),
                ephemeral=True,
            )

    @bot.tree.command(name="whoami", description="Check your current active persona(s)")
    async def whoami(interaction: discord.Interaction):
        """Show the user's current active persona(s)."""
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer (Discord API latency)
            return

        user_id = str(interaction.user.id)

        # Check for ensemble mode (multiple personas)
        active_personas = bot.agent_core.get_active_personas(user_id)

        if not active_personas:
            await interaction.followup.send(
                f"You don't have an active persona.\n"
                f"Use `/swap <persona_id>` to select one, or\n"
                f"Use `/persona load <persona_id>` to load multiple personas.",
                ephemeral=True,
            )
            return

        # If ensemble mode (multiple personas)
        if len(active_personas) > 1:
            response = (
                f"**🎭 Ensemble Mode Active** ({len(active_personas)} personas)\n\n"
            )

            for persona in active_personas:
                # Check if narrator
                if persona.is_narrator:
                    response += (
                        f"**{persona.name}** (`{persona.persona_id}`) 🎲 **[NARRATOR]**\n"
                        f"• Role: Omniscient environmental narrator\n"
                        f"• Temp: {persona.temperature} | Tokens: {persona.max_tokens}\n\n"
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
                        f"**{persona.name}** (`{persona.persona_id}`){bg_indicator}{img_indicator}\n"
                        f"• Traits: {traits}\n"
                        f"• Temp: {persona.temperature} | Tokens: {persona.max_tokens}\n\n"
                    )

            response += "The AI is controlling multiple characters as Dungeon Master/Narrator.\n"
            response += "\n📖 = Has background | 🖼️ = Has appearance images | 🎲 = Narrator (no body)"

            await interaction.followup.send(response, ephemeral=True)
        else:
            # Single persona mode
            persona = active_personas[0]
            traits = (
                ", ".join(persona.personality_traits)
                if persona.personality_traits
                else "None"
            )

            # Build response with background info if available
            response = (
                f"**Current Persona:**\n"
                f"• ID: `{persona.persona_id}`\n"
                f"• Name: **{persona.name}**\n"
                f"• Traits: {traits}\n"
                f"• Temperature: {persona.temperature}\n"
                f"• Max Tokens: {persona.max_tokens}"
            )

            if persona.background:
                # Show "Has background" indicator with character count
                # User can use /persona view_background to see full text
                response += f"\n• Background: ✓ Defined ({len(persona.background)} chars) - use `/persona view_background {persona.persona_id}` to view"

            await interaction.followup.send(
                response,
                ephemeral=True,
            )

"""
Discord Frontend Adapter - Platform bridge for Project Myriad.

This module bridges Discord to the platform-agnostic AgentCore.
It handles Discord-specific events and commands, but ALL intelligence
and state management happens in AgentCore.

Following the Adapter Pattern: This module can be swapped for Telegram, CLI, etc.
without touching the core logic.
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from core.agent_core import AgentCore


class MyriadDiscordBot(commands.Bot):
    """Discord bot that wraps the AgentCore engine."""

    def __init__(self, agent_core: AgentCore):
        """
        Initialize the Discord bot.

        Args:
            agent_core: The platform-agnostic AI engine
        """
        # Discord bot setup with message content intent
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        # Store reference to core engine
        self.agent_core = agent_core

    async def setup_hook(self):
        """Setup hook called when bot is ready."""
        # Sync slash commands
        await self.tree.sync()
        print("Slash commands synced!")

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        print(f"✓ Myriad Discord Adapter online")
        print(f"✓ Connected as: {self.user}")
        print(f"✓ Bot ID: {self.user.id}")
        print(f"✓ Available personas: {', '.join(self.agent_core.list_personas())}")

    async def on_message(self, message: discord.Message):
        """
        Handle incoming messages.

        Messages that mention the bot are processed by the AgentCore.
        """
        # Ignore bot's own messages
        if message.author == self.user:
            return

        # Only respond to mentions
        if self.user not in message.mentions:
            return

        # Extract user ID as string (platform-agnostic format)
        user_id = str(message.author.id)

        # Remove bot mention from message
        content = message.content.replace(f"<@{self.user.id}>", "").strip()

        if not content:
            return

        # Check if user has an active persona
        active_persona = self.agent_core.get_active_persona(user_id)

        if not active_persona:
            await message.channel.send(
                f"{message.author.mention} You don't have an active persona. "
                f"Use `/swap <persona_id>` to select one.\n"
                f"Available personas: {', '.join(self.agent_core.list_personas())}"
            )
            return

        # Show typing indicator
        async with message.channel.typing():
            # Process message through AgentCore
            response = self.agent_core.process_message(
                user_id=user_id,
                message=content,
                memory_visibility="ISOLATED",  # Default to persona-specific memories
            )

        # Send response
        if response:
            await message.channel.send(response)
        else:
            await message.channel.send(
                f"{message.author.mention} Error processing your message. "
                f"Please check the bot logs."
            )


def create_discord_bot(agent_core: AgentCore) -> MyriadDiscordBot:
    """
    Factory function to create and configure the Discord bot.

    Args:
        agent_core: The platform-agnostic AI engine

    Returns:
        Configured MyriadDiscordBot instance
    """
    bot = MyriadDiscordBot(agent_core)

    # ========================
    # SLASH COMMANDS
    # ========================

    @bot.tree.command(name="swap", description="Switch to a different persona")
    @app_commands.describe(persona_id="The ID of the persona to switch to")
    async def swap_persona(interaction: discord.Interaction, persona_id: str):
        """Switch the user's active persona."""
        user_id = str(interaction.user.id)

        # Attempt to switch persona
        success = bot.agent_core.switch_persona(user_id, persona_id)

        if success:
            persona = bot.agent_core.get_active_persona(user_id)
            if persona:  # Type guard to satisfy type checker
                await interaction.response.send_message(
                    f"✓ Switched to persona: **{persona.name}** (`{persona_id}`)",
                    ephemeral=True,
                )
        else:
            available = bot.agent_core.list_personas()
            await interaction.response.send_message(
                f"✗ Persona '{persona_id}' not found.\n"
                f"Available personas: {', '.join(available)}",
                ephemeral=True,
            )

    @bot.tree.command(name="personas", description="List all available personas")
    async def list_personas(interaction: discord.Interaction):
        """List all available persona cartridges."""
        personas = bot.agent_core.list_personas()

        if personas:
            persona_list = "\n".join([f"• `{p}`" for p in personas])
            await interaction.response.send_message(
                f"**Available Personas:**\n{persona_list}\n\n"
                f"Use `/swap <persona_id>` to switch.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "No personas found in the `personas/` directory.", ephemeral=True
            )

    @bot.tree.command(name="whoami", description="Check your current active persona")
    async def whoami(interaction: discord.Interaction):
        """Show the user's current active persona."""
        user_id = str(interaction.user.id)
        persona = bot.agent_core.get_active_persona(user_id)

        if persona:
            traits = (
                ", ".join(persona.personality_traits)
                if persona.personality_traits
                else "None"
            )
            await interaction.response.send_message(
                f"**Current Persona:**\n"
                f"• ID: `{persona.persona_id}`\n"
                f"• Name: **{persona.name}**\n"
                f"• Traits: {traits}\n"
                f"• Temperature: {persona.temperature}\n"
                f"• Max Tokens: {persona.max_tokens}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"You don't have an active persona.\n"
                f"Use `/swap <persona_id>` to select one.",
                ephemeral=True,
            )

    @bot.tree.command(name="forget", description="Clear your conversation memory")
    @app_commands.describe(
        persona_id="Optional: Clear only memories from this persona. Leave blank to clear ALL."
    )
    async def forget(
        interaction: discord.Interaction, persona_id: Optional[str] = None
    ):
        """Clear conversation memory for the user."""
        user_id = str(interaction.user.id)

        # Clear memories
        bot.agent_core.clear_user_memory(user_id, persona_id)

        if persona_id:
            await interaction.response.send_message(
                f"✓ Cleared all memories from persona `{persona_id}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "✓ Cleared ALL conversation memories.", ephemeral=True
            )

    @bot.tree.command(name="stats", description="View your memory statistics")
    async def stats(interaction: discord.Interaction):
        """Show memory statistics for the user."""
        user_id = str(interaction.user.id)
        stats = bot.agent_core.get_memory_stats(user_id)

        await interaction.response.send_message(
            f"**Memory Statistics:**\n"
            f"• Total Memories: {stats['total_memories']}\n"
            f"• Global (Shared): {stats['global_memories']}\n"
            f"• Isolated (Persona-specific): {stats['isolated_memories']}\n"
            f"• Active Persona: `{stats['active_persona'] or 'None'}`",
            ephemeral=True,
        )

    return bot


# ========================
# ENTRY POINT
# ========================


def run_discord_adapter():
    """Main entry point for the Discord adapter."""
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    discord_token = os.getenv("DISCORD_TOKEN")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4")
    memory_limit = int(os.getenv("MEMORY_CONTEXT_LIMIT", "50"))

    # Validate environment
    if not discord_token:
        raise ValueError("DISCORD_TOKEN not found in environment")
    if not api_key:
        raise ValueError("LLM_API_KEY not found in environment")

    # Initialize AgentCore (platform-agnostic)
    agent_core = AgentCore(
        api_key=api_key, base_url=base_url, model=model, memory_limit=memory_limit
    )

    # Create Discord adapter
    bot = create_discord_bot(agent_core)

    # Run bot
    print("Starting Myriad Discord Adapter...")
    bot.run(discord_token)


if __name__ == "__main__":
    run_discord_adapter()

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
from core.vision_bridge import VisionBridge
from core.config import MyriadConfig
from database.activity_tracker import ActivityTracker
from adapters.commands.persona_commands import register_persona_commands
from adapters.commands.memory_commands import register_memory_commands
from adapters.commands.lives_commands import register_lives_commands
from adapters.commands.saves_commands import register_saves_commands


# ========================
# HELPER FUNCTIONS
# ========================


def chunk_message(text: str, max_length: int = 2000) -> list[str]:
    """
    Split a message into chunks that fit within Discord's character limit.

    Args:
        text: The message to split
        max_length: Maximum characters per chunk (default: 2000 for Discord)

    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by lines first to preserve formatting
    lines = text.split("\n")

    for line in lines:
        # If a single line is longer than max_length, split it by words
        if len(line) > max_length:
            words = line.split(" ")
            for word in words:
                # If a single word is longer than max_length, force character split
                while len(word) > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.rstrip())
                        current_chunk = ""
                    chunks.append(word[:max_length])
                    word = word[max_length:]

                # Add the remaining word
                if len(current_chunk) + len(word) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.rstrip())
                    current_chunk = word + " "
                else:
                    current_chunk += word + " "
        else:
            # Check if adding this line would exceed the limit
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.rstrip())

    return chunks


# ========================
# DISCORD UI COMPONENTS
# ========================


class VisionAttachmentModal(discord.ui.Modal, title="Send Message with Image"):
    """Modal for sending a message along with an uploaded image."""

    message_input = discord.ui.TextInput(
        label="Your Message",
        style=discord.TextStyle.paragraph,
        placeholder="Type your message here (or leave blank)...",
        required=False,
        max_length=2000,
    )

    async def branch(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "branch"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(
        label="Forget Forever", style=discord.ButtonStyle.danger, emoji="🗑️"
    )
    async def forget(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "forget"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = None
        self.stop()
        await interaction.response.defer()


class MyriadDiscordBot(commands.Bot):
    """Discord bot that wraps the AgentCore engine."""

    def __init__(
        self, agent_core: AgentCore, vision_bridge: Optional[VisionBridge] = None
    ):
        """
        Initialize the Discord bot.

        Args:
            agent_core: The platform-agnostic AI engine
            vision_bridge: Optional vision processing bridge for image handling
        """
        # Discord bot setup with message content intent
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        # Store reference to core engine
        self.agent_core = agent_core
        self.vision_bridge = vision_bridge

        # Initialize activity tracker for circadian rhythm engine
        self.activity_tracker = ActivityTracker()

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

        Messages that mention the bot OR are in DMs are processed by the AgentCore.
        If image attachments are present, they are processed through the vision bridge.
        """
        # Ignore bot's own messages
        if message.author == self.user:
            return

        # Check if this is a DM or a mention
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.user in message.mentions

        # Only respond to mentions in servers, or any message in DMs
        if not is_dm and not is_mentioned:
            return

        # Extract user ID as string (platform-agnostic format)
        user_id = str(message.author.id)

        # Remove bot mention from message (if present)
        content = message.content.replace(f"<@{self.user.id}>", "").strip()

        # If no text content but has attachments, default to empty message
        if not content and message.attachments:
            content = "(no text message)"

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

        # Log activity for circadian rhythm tracking
        self.activity_tracker.log_activity(user_id, active_persona.persona_id)

        # Track last channel for spontaneous outreach
        self.activity_tracker.update_last_channel(user_id, str(message.channel.id))

        # Process image attachments if present (Split-Brain Vision Pipeline)
        vision_description = None
        if message.attachments and self.vision_bridge:
            for attachment in message.attachments:
                # Check if attachment is an image
                if attachment.content_type and attachment.content_type.startswith(
                    "image/"
                ):
                    try:
                        # Download image bytes
                        image_bytes = await attachment.read()

                        # Extract image format from content type
                        image_format = attachment.content_type.split("/")[-1]

                        # Process through vision bridge
                        description = self.vision_bridge.process_image_bytes(
                            image_bytes, image_format
                        )

                        if description:
                            vision_description = description
                            print(f"[Vision] Processed image: {description[:100]}...")
                            break  # Only process first image
                    except Exception as e:
                        print(f"[Vision] Error processing attachment: {e}")

        # Show typing indicator
        async with message.channel.typing():
            # Process message through AgentCore (with vision description if available)
            response = self.agent_core.process_message(
                user_id=user_id,
                message=content,
                memory_visibility="ISOLATED",  # Default to persona-specific memories
                vision_description=vision_description,
            )

        # Send response
        if response:
            # Chunk the response to fit Discord's 2000 character limit
            chunks = chunk_message(response, max_length=2000)
            for chunk in chunks:
                await message.channel.send(chunk)
        else:
            await message.channel.send(
                f"{message.author.mention} Error processing your message. "
                f"Please check the bot logs."
            )


def create_discord_bot(
    agent_core: AgentCore, vision_bridge: Optional[VisionBridge] = None
) -> MyriadDiscordBot:
    """
    Factory function to create and configure the Discord bot.

    Args:
        agent_core: The platform-agnostic AI engine
        vision_bridge: Optional vision processing bridge

    Returns:
        Configured MyriadDiscordBot instance
    """
    bot = MyriadDiscordBot(agent_core, vision_bridge)

    # ========================
    # REGISTER COMMAND MODULES
    # ========================

    # Persona management commands (swap, personas, whoami)
    register_persona_commands(bot)
    register_memory_commands(bot)
    register_lives_commands(bot)
    register_saves_commands(bot)

    return bot


# ========================
# ENTRY POINT
# ========================


def run_discord_adapter():
    """Main entry point for the Discord adapter."""
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Load configuration
    config = MyriadConfig.from_env()
    print(f"Loaded configuration: {config}")

    # Initialize AgentCore (platform-agnostic) - now simplified with MyriadConfig
    agent_core = AgentCore(config=config)

    # Initialize VisionBridge if configured
    vision_bridge = None
    if config.vision.enabled:
        try:
            vision_bridge = VisionBridge(
                vision_api_key=config.vision.api_key,
                vision_base_url=config.vision.base_url,
                vision_model=config.vision.model,
            )
            print(f"✓ Vision Bridge enabled: {config.vision.base_url}")
        except Exception as e:
            print(f"⚠ Vision Bridge initialization failed: {e}")
            print("  Continuing without vision support...")
    else:
        print("ℹ Vision Bridge not configured (set VISION_BASE_URL to enable)")

    # Create Discord adapter
    bot = create_discord_bot(agent_core, vision_bridge)

    # Run bot
    print("Starting Myriad Discord Adapter...")
    bot.run(config.discord_token)


if __name__ == "__main__":
    run_discord_adapter()

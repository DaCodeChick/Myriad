"""
Discord bot implementation for Project Myriad.

Main MyriadDiscordBot class that bridges Discord to the platform-agnostic AgentCore.

RDSSC Phase 2: Updated imports to use feature-organized command packages.
"""

from typing import Optional

import discord
from discord.ext import commands

from core.agent_core import AgentCore
from core.vision_bridge import VisionBridge
from core.vision_cache_service import VisionCacheService
from core.features.roleplay.activity_tracker import ActivityTracker
from adapters.discord.event_handlers import EventHandlers
from adapters.discord.vision_processor import VisionProcessor

# Command imports - reorganized by feature
from adapters.commands.config_commands import register_config_commands
from adapters.commands.roleplay import register_roleplay_commands
from adapters.commands.memory.memory_commands import register_memory_commands
from adapters.commands.memory.search_cache_commands import (
    setup_commands as setup_cache_commands,
)


class MyriadDiscordBot(commands.Bot):
    """Discord bot that wraps the AgentCore engine."""

    def __init__(
        self,
        agent_core: AgentCore,
        vision_bridge: Optional[VisionBridge] = None,
        vision_cache_service: Optional[VisionCacheService] = None,
    ):
        """
        Initialize the Discord bot.

        Args:
            agent_core: The platform-agnostic AI engine
            vision_bridge: Optional vision processing bridge for image handling
            vision_cache_service: Optional vision cache service for character appearance
        """
        # Discord bot setup with message content intent
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        # Store reference to core engine and vision services
        self.agent_core = agent_core
        self.vision_bridge = vision_bridge
        self.vision_cache_service = vision_cache_service

        # Initialize activity tracker for circadian rhythm engine
        self.activity_tracker = ActivityTracker()

        # Initialize vision processor
        self.vision_processor = VisionProcessor(vision_bridge=vision_bridge)

        # Initialize event handlers
        self.event_handlers = EventHandlers(
            bot=self,
            agent_core=agent_core,
            activity_tracker=self.activity_tracker,
            vision_processor=self.vision_processor,
        )
        print("✓ Bot initialization complete")

    async def setup_hook(self):
        """Setup hook called when bot is ready."""
        print("→ setup_hook() called", flush=True)
        # Sync slash commands with timeout
        try:
            print("→ Syncing slash commands to Discord...", flush=True)
            await self.tree.sync()
            print("✓ Slash commands synced!", flush=True)
        except Exception as e:
            print(f"⚠ Failed to sync slash commands: {e}", flush=True)
            print("  Bot will continue but commands may not be available", flush=True)
        print("✓ setup_hook() completed", flush=True)

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        print("→ on_ready() called", flush=True)
        await self.event_handlers.on_ready()
        print("✓ on_ready() completed", flush=True)

    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        await self.event_handlers.on_message(message)


def create_discord_bot(
    agent_core: AgentCore,
    vision_bridge: Optional[VisionBridge] = None,
    vision_cache_service: Optional[VisionCacheService] = None,
) -> MyriadDiscordBot:
    """
    Factory function to create and configure the Discord bot.

    Args:
        agent_core: The platform-agnostic AI engine
        vision_bridge: Optional vision processing bridge
        vision_cache_service: Optional vision cache service for character appearance

    Returns:
        Configured MyriadDiscordBot instance
    """
    print("→ Creating MyriadDiscordBot instance...", flush=True)
    bot = MyriadDiscordBot(agent_core, vision_bridge, vision_cache_service)
    print("✓ MyriadDiscordBot instance created", flush=True)

    # ========================
    # REGISTER COMMAND MODULES
    # ========================
    # RDSSC Phase 2: Commands now organized by feature

    # Core config commands
    print("→ Registering config commands...", flush=True)
    register_config_commands(bot)

    # Roleplay feature commands (all persona, limbic, lives, masks, scenarios, etc.)
    print("→ Registering roleplay commands...", flush=True)
    register_roleplay_commands(bot)

    # Memory system commands
    print("→ Registering memory commands...", flush=True)
    register_memory_commands(bot)
    print("→ Setting up cache commands...", flush=True)
    setup_cache_commands(bot.tree)

    print("✓ All commands registered", flush=True)
    return bot

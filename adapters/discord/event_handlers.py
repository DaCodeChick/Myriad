"""
Discord event handlers for Project Myriad.

Handles Discord events like on_ready, on_message, and autonomy check loops.
"""

import os
from typing import Optional, Callable, Awaitable

import discord
from discord.ext import tasks

from core.agent_core import AgentCore
from core.autonomy_engine import AutonomyEngine
from database.activity_tracker import ActivityTracker
from adapters.discord.utils import chunk_message
from adapters.discord.vision_processor import VisionProcessor


class EventHandlers:
    """Manages Discord event handlers and autonomy loops."""

    def __init__(
        self,
        bot: discord.Client,
        agent_core: AgentCore,
        activity_tracker: ActivityTracker,
        vision_processor: VisionProcessor,
    ):
        """
        Initialize event handlers.

        Args:
            bot: Discord bot instance
            agent_core: Platform-agnostic AI engine
            activity_tracker: Activity tracking for circadian rhythm
            vision_processor: Vision processing for image attachments
        """
        self.bot = bot
        self.agent_core = agent_core
        self.activity_tracker = activity_tracker
        self.vision_processor = vision_processor

        # Autonomy engine setup
        self.autonomy_engine: Optional[AutonomyEngine] = None
        self.autonomy_enabled = os.getenv("AUTONOMY_ENABLED", "false").lower() == "true"
        self.autonomy_interval = int(os.getenv("AUTONOMY_CHECK_INTERVAL", "60"))

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        print(f"✓ Myriad Discord Adapter online")
        print(f"✓ Connected as: {self.bot.user}")
        print(f"✓ Bot ID: {self.bot.user.id}")
        print(f"✓ Available personas: {', '.join(self.agent_core.list_personas())}")

        # Log whitelisted bots
        whitelisted_bots = self.agent_core.config.discord.whitelisted_bot_ids
        if whitelisted_bots:
            print(
                f"✓ Whitelisted bot IDs: {', '.join(str(id) for id in whitelisted_bots)}"
            )
        else:
            print("ℹ No whitelisted bots configured (ignoring all bot messages)")

        # Initialize and start autonomy engine if enabled
        if self.autonomy_enabled:
            self._initialize_autonomy_engine()
            self._start_autonomy_loop()

    def _initialize_autonomy_engine(self) -> None:
        """Initialize the autonomy engine with shared resources from AgentCore."""
        try:
            self.autonomy_engine = AutonomyEngine(
                llm_client=self.agent_core.provider,
                activity_tracker=self.activity_tracker,
                user_state=self.agent_core.memory_matrix,
                persona_loader=self.agent_core.persona_loader,
                user_preferences=self.agent_core.user_preferences,
                limbic_engine=self.agent_core.limbic_engine,
            )
            print(
                f"✓ Autonomy Engine initialized (interval: {self.autonomy_interval}min)"
            )
        except Exception as e:
            print(f"⚠ Autonomy Engine initialization failed: {e}")
            self.autonomy_enabled = False

    def _start_autonomy_loop(self) -> None:
        """Start the autonomy check loop."""
        if not self.autonomy_check_loop.is_running():
            # Dynamically set the loop interval based on config
            self.autonomy_check_loop.change_interval(minutes=self.autonomy_interval)
            self.autonomy_check_loop.start()
            print(f"✓ Autonomy loop started (every {self.autonomy_interval} minutes)")

    @tasks.loop(minutes=60)  # Default interval, changed dynamically
    async def autonomy_check_loop(self):
        """Background task that checks all users for spontaneous outreach."""
        if not self.autonomy_engine:
            return

        print("\n[Autonomy] Running scheduled check...")

        try:
            users = self.autonomy_engine.get_all_active_users()
            print(f"[Autonomy] Checking {len(users)} users for potential outreach")

            for user_id in users:
                await self.autonomy_engine.check_user_for_outreach(
                    user_id=user_id,
                    send_callback=self._send_spontaneous_message,
                )

            # Periodic cleanup of old activity logs
            deleted = self.autonomy_engine.cleanup_old_activity_logs(days_to_keep=30)
            if deleted > 0:
                print(f"[Autonomy] Cleaned up {deleted} old activity records")

        except Exception as e:
            print(f"[Autonomy] Error during check loop: {e}")

    @autonomy_check_loop.before_loop
    async def before_autonomy_check(self):
        """Wait until the bot is ready before starting the autonomy loop."""
        await self.bot.wait_until_ready()

    async def _send_spontaneous_message(self, user_id: str, message: str) -> bool:
        """
        Send a spontaneous message to a user's last known channel.

        Args:
            user_id: Discord user ID
            message: Message content to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # Get the user's last known channel
            channel_id = self.activity_tracker.get_last_channel(user_id)
            if not channel_id:
                print(f"[Autonomy] No last channel found for user {user_id}")
                return False

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                # Try to fetch the channel if not in cache
                try:
                    channel = await self.bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    print(f"[Autonomy] Channel {channel_id} not found")
                    return False

            # Send the message (chunked if needed)
            chunks = chunk_message(message, max_length=2000)
            for chunk in chunks:
                await channel.send(chunk)

            # Log this activity
            active_persona = self.agent_core.get_active_persona(user_id)
            if active_persona:
                self.activity_tracker.log_activity(user_id, active_persona.persona_id)

            return True

        except Exception as e:
            print(f"[Autonomy] Error sending spontaneous message to {user_id}: {e}")
            return False

    async def on_message(self, message: discord.Message):
        """
        Handle incoming messages.

        Messages that mention the bot OR are in DMs are processed by the AgentCore.
        If image attachments are present, they are processed through the vision bridge.

        Bot messages are ignored unless the bot ID is in WHITELISTED_BOT_IDS.
        """
        # Ignore bot's own messages
        if message.author == self.bot.user:
            return

        # Handle bot messages: check whitelist
        if message.author.bot:
            whitelisted_bots = self.agent_core.config.discord.whitelisted_bot_ids
            if message.author.id not in whitelisted_bots:
                return  # Ignore non-whitelisted bots

        # Check if this is a DM or a mention
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions

        # Only respond to mentions in servers, or any message in DMs
        if not is_dm and not is_mentioned:
            return

        # Extract user ID as string (platform-agnostic format)
        user_id = str(message.author.id)

        # Remove bot mention from message (if present)
        content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

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

        # Extract image attachments for native vision support (Gemini)
        image_data = None
        vision_description = None

        if message.attachments:
            # Check if provider supports native vision (Gemini)
            if self.agent_core.provider.provider_name == "gemini":
                # Extract image bytes for native Gemini vision
                image_data = []
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith(
                        "image/"
                    ):
                        try:
                            image_bytes = await attachment.read()
                            mime_type = attachment.content_type
                            image_data.append((image_bytes, mime_type))
                            print(
                                f"[Vision] Attached image: {attachment.filename} ({mime_type})"
                            )
                        except Exception as e:
                            print(f"[Vision] Error downloading attachment: {e}")

                # Convert to None if empty
                if not image_data:
                    image_data = None
            else:
                # Fallback to split-brain vision pipeline for non-Gemini providers
                vision_description = await self.vision_processor.process_attachments(
                    message
                )

        # Show typing indicator
        async with message.channel.typing():
            # Process message through AgentCore (with native vision or description)
            response = self.agent_core.process_message(
                user_id=user_id,
                message=content,
                memory_visibility="ISOLATED",  # Default to persona-specific memories
                vision_description=vision_description,
                image_data=image_data,
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

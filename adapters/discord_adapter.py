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
# CONFIRMATION VIEWS
# ========================


class ConfirmationView(discord.ui.View):
    """Generic confirmation dialog with Yes/No buttons."""

    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


class BranchOrForgetView(discord.ui.View):
    """Save state load dialog with BRANCH/FORGET choice."""

    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.value: Optional[str] = None  # "branch", "forget", or None

    @discord.ui.button(
        label="Save as New Branch", style=discord.ButtonStyle.primary, emoji="🌿"
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

    # ========================
    # LIVES COMMAND GROUP (Timeline Branching)
    # ========================

    if bot.agent_core.lives_enabled:
        life_group = app_commands.Group(
            name="life", description="Manage alternate timelines (Lives)"
        )

        @life_group.command(name="new", description="Create a new timeline")
        @app_commands.describe(
            name="Name for the new timeline", description="Description of this timeline"
        )
        async def life_new(
            interaction: discord.Interaction, name: str, description: str
        ):
            """Create a new life/timeline."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            # Confirmation
            view = ConfirmationView()
            await interaction.response.send_message(
                f"Create new timeline **{name}**?\n"
                f"Description: {description}\n\n"
                f"This will create a fresh timeline branch.",
                view=view,
                ephemeral=True,
            )

            await view.wait()

            if view.value:
                try:
                    life_id = bot.agent_core.lives_engine.create_life(
                        user_id=user_id,
                        persona_id=persona.persona_id,
                        name=name,
                        description=description,
                    )
                    await interaction.edit_original_response(
                        content=f"✓ Created new timeline: **{name}** (ID: {life_id})",
                        view=None,
                    )
                except Exception as e:
                    await interaction.edit_original_response(
                        content=f"✗ Failed to create timeline: {str(e)}", view=None
                    )
            else:
                await interaction.edit_original_response(
                    content="Cancelled.", view=None
                )

        @life_group.command(name="switch", description="Switch to a different timeline")
        @app_commands.describe(name="Name of the timeline to switch to")
        async def life_switch(interaction: discord.Interaction, name: str):
            """Switch to a different life/timeline."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            try:
                bot.agent_core.lives_engine.switch_life(
                    user_id=user_id, persona_id=persona.persona_id, life_name=name
                )
                await interaction.response.send_message(
                    f"✓ Switched to timeline: **{name}**", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"✗ Failed to switch timeline: {str(e)}", ephemeral=True
                )

        @life_group.command(name="list", description="List all timelines")
        async def life_list(interaction: discord.Interaction):
            """List all lives/timelines for the user."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            lives = bot.agent_core.lives_engine.list_lives(
                user_id=user_id, persona_id=persona.persona_id
            )

            if not lives:
                await interaction.response.send_message(
                    "No timelines found.", ephemeral=True
                )
                return

            lines = ["**Your Timelines:**\n"]
            for life in lives:
                active_marker = " ✓ **[ACTIVE]**" if life["is_active"] else ""
                lines.append(
                    f"• **{life['name']}**{active_marker}\n  _{life['description']}_"
                )

            await interaction.response.send_message("\n".join(lines), ephemeral=True)

        @life_group.command(name="delete", description="Delete a timeline")
        @app_commands.describe(name="Name of the timeline to delete")
        async def life_delete(interaction: discord.Interaction, name: str):
            """Delete a life/timeline."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            # Confirmation
            view = ConfirmationView()
            await interaction.response.send_message(
                f"⚠️ Delete timeline **{name}**?\n\n"
                f"This will permanently delete all messages and save states in this timeline.",
                view=view,
                ephemeral=True,
            )

            await view.wait()

            if view.value:
                try:
                    bot.agent_core.lives_engine.delete_life(
                        user_id=user_id, persona_id=persona.persona_id, life_name=name
                    )
                    await interaction.edit_original_response(
                        content=f"✓ Deleted timeline: **{name}**", view=None
                    )
                except Exception as e:
                    await interaction.edit_original_response(
                        content=f"✗ Failed to delete timeline: {str(e)}", view=None
                    )
            else:
                await interaction.edit_original_response(
                    content="Cancelled.", view=None
                )

        bot.tree.add_command(life_group)

    # ========================
    # MEMORY COMMAND GROUP (Save States)
    # ========================

    if bot.agent_core.lives_enabled:
        memory_group = app_commands.Group(
            name="memory", description="Manage save states (Memories)"
        )

        @memory_group.command(name="save", description="Create a save state")
        @app_commands.describe(
            name="Name for this save state",
            description="Description of this checkpoint",
        )
        async def memory_save(
            interaction: discord.Interaction, name: str, description: str
        ):
            """Create a save state at the current message."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            # Get active life
            active_life = bot.agent_core.lives_engine.get_active_life(
                user_id=user_id, persona_id=persona.persona_id
            )

            if not active_life:
                await interaction.response.send_message(
                    "No active timeline found.", ephemeral=True
                )
                return

            life_id = active_life["life_id"]

            # Get latest message ID as the checkpoint
            checkpoint_message_id = (
                bot.agent_core.save_states_engine.get_latest_message_id(life_id=life_id)
            )

            if not checkpoint_message_id:
                await interaction.response.send_message(
                    "No messages found in this timeline to save.", ephemeral=True
                )
                return

            try:
                save_id = bot.agent_core.save_states_engine.create_save_state(
                    life_id=life_id,
                    name=name,
                    description=description,
                    checkpoint_message_id=checkpoint_message_id,
                )
                await interaction.response.send_message(
                    f"✓ Created save state: **{name}** (ID: {save_id})",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"✗ Failed to create save state: {str(e)}", ephemeral=True
                )

        @memory_group.command(name="load", description="Load a save state")
        @app_commands.describe(name="Name of the save state to load")
        async def memory_load(interaction: discord.Interaction, name: str):
            """Load a save state with BRANCH/FORGET choice."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            # Get active life
            active_life = bot.agent_core.lives_engine.get_active_life(
                user_id=user_id, persona_id=persona.persona_id
            )

            if not active_life:
                await interaction.response.send_message(
                    "No active timeline found.", ephemeral=True
                )
                return

            life_id = active_life["life_id"]

            # Get save state
            try:
                save_state = bot.agent_core.save_states_engine.get_save_state(
                    life_id=life_id, name=name
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"✗ Save state not found: {str(e)}", ephemeral=True
                )
                return

            # Count messages to be affected
            messages_count = (
                bot.agent_core.save_states_engine.count_messages_after_checkpoint(
                    life_id=life_id,
                    checkpoint_message_id=save_state["checkpoint_message_id"],
                )
            )

            # Show BRANCH/FORGET dialog
            view = BranchOrForgetView()
            await interaction.response.send_message(
                f"⚠️ Loading save state **{name}** will affect {messages_count} messages.\n\n"
                f"**What would you like to do?**\n"
                f"🌿 **Save as New Branch**: Current timeline becomes a new branch, then rewind\n"
                f"🗑️ **Forget Forever**: Delete all messages after this checkpoint (irreversible)",
                view=view,
                ephemeral=True,
            )

            await view.wait()

            if view.value == "branch":
                # Save current timeline as a new branch
                try:
                    new_life_name = f"{active_life['name']} (branch)"
                    new_life_id = bot.agent_core.lives_engine.create_life(
                        user_id=user_id,
                        persona_id=persona.persona_id,
                        name=new_life_name,
                        description=f"Branch from {active_life['name']} before loading save state '{name}'",
                    )

                    # Clone all memories to the new life
                    bot.agent_core.memory_matrix.clone_life_memories(
                        source_life_id=life_id, target_life_id=new_life_id
                    )

                    # Delete messages after checkpoint in original life
                    deleted_count = (
                        bot.agent_core.memory_matrix.delete_memories_after_checkpoint(
                            life_id=life_id,
                            checkpoint_message_id=save_state["checkpoint_message_id"],
                        )
                    )

                    await interaction.edit_original_response(
                        content=f"✓ Created branch **{new_life_name}** (ID: {new_life_id})\n"
                        f"✓ Rewound timeline to save state **{name}** ({deleted_count} messages removed)",
                        view=None,
                    )
                except Exception as e:
                    await interaction.edit_original_response(
                        content=f"✗ Failed to branch and load: {str(e)}", view=None
                    )

            elif view.value == "forget":
                # Delete messages after checkpoint (permanent)
                try:
                    deleted_count = (
                        bot.agent_core.memory_matrix.delete_memories_after_checkpoint(
                            life_id=life_id,
                            checkpoint_message_id=save_state["checkpoint_message_id"],
                        )
                    )
                    await interaction.edit_original_response(
                        content=f"✓ Loaded save state **{name}** ({deleted_count} messages permanently deleted)",
                        view=None,
                    )
                except Exception as e:
                    await interaction.edit_original_response(
                        content=f"✗ Failed to load: {str(e)}", view=None
                    )
            else:
                await interaction.edit_original_response(
                    content="Cancelled.", view=None
                )

        @memory_group.command(name="list", description="List all save states")
        async def memory_list(interaction: discord.Interaction):
            """List all save states in the current timeline."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            # Get active life
            active_life = bot.agent_core.lives_engine.get_active_life(
                user_id=user_id, persona_id=persona.persona_id
            )

            if not active_life:
                await interaction.response.send_message(
                    "No active timeline found.", ephemeral=True
                )
                return

            life_id = active_life["life_id"]

            save_states = bot.agent_core.save_states_engine.list_save_states(
                life_id=life_id
            )

            if not save_states:
                await interaction.response.send_message(
                    "No save states found in this timeline.", ephemeral=True
                )
                return

            lines = ["**Save States in Current Timeline:**\n"]
            for save in save_states:
                lines.append(
                    f"• **{save['name']}** (ID: {save['save_id']})\n  _{save['description']}_"
                )

            await interaction.response.send_message("\n".join(lines), ephemeral=True)

        @memory_group.command(name="delete", description="Delete a save state")
        @app_commands.describe(name="Name of the save state to delete")
        async def memory_delete(interaction: discord.Interaction, name: str):
            """Delete a save state."""
            user_id = str(interaction.user.id)
            persona = bot.agent_core.get_active_persona(user_id)

            if not persona:
                await interaction.response.send_message(
                    "You don't have an active persona. Use `/swap <persona_id>` first.",
                    ephemeral=True,
                )
                return

            # Get active life
            active_life = bot.agent_core.lives_engine.get_active_life(
                user_id=user_id, persona_id=persona.persona_id
            )

            if not active_life:
                await interaction.response.send_message(
                    "No active timeline found.", ephemeral=True
                )
                return

            life_id = active_life["life_id"]

            # Confirmation
            view = ConfirmationView()
            await interaction.response.send_message(
                f"Delete save state **{name}**?\n\n"
                f"This only deletes the checkpoint marker, not the messages.",
                view=view,
                ephemeral=True,
            )

            await view.wait()

            if view.value:
                try:
                    bot.agent_core.save_states_engine.delete_save_state(
                        life_id=life_id, name=name
                    )
                    await interaction.edit_original_response(
                        content=f"✓ Deleted save state: **{name}**", view=None
                    )
                except Exception as e:
                    await interaction.edit_original_response(
                        content=f"✗ Failed to delete save state: {str(e)}", view=None
                    )
            else:
                await interaction.edit_original_response(
                    content="Cancelled.", view=None
                )

        bot.tree.add_command(memory_group)

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

    # Memory configuration
    short_term_limit = int(os.getenv("SHORT_TERM_MEMORY_LIMIT", "10"))

    # Vector memory configuration
    vector_memory_enabled = os.getenv("VECTOR_MEMORY_ENABLED", "true").lower() == "true"
    semantic_recall_limit = int(os.getenv("SEMANTIC_RECALL_LIMIT", "5"))

    # Tool use configuration
    tools_enabled = os.getenv("TOOLS_ENABLED", "true").lower() == "true"
    max_tool_iterations = int(os.getenv("MAX_TOOL_ITERATIONS", "5"))

    # Knowledge graph memory configuration
    graph_memory_enabled = os.getenv("GRAPH_MEMORY_ENABLED", "true").lower() == "true"
    graph_db_path = os.getenv("GRAPH_DB_PATH", "data/knowledge_graph.db")

    # Limbic system configuration (emotional neurochemistry)
    limbic_enabled = os.getenv("LIMBIC_ENABLED", "true").lower() == "true"
    limbic_db_path = os.getenv("LIMBIC_DB_PATH", "data/limbic_state.db")

    # Digital Pharmacy configuration (substance-based limbic overrides)
    digital_pharmacy_enabled = (
        os.getenv("DIGITAL_PHARMACY_ENABLED", "true").lower() == "true"
    )

    # Cadence Degradation Engine configuration (text post-processing)
    cadence_degrader_enabled = (
        os.getenv("CADENCE_DEGRADER_ENABLED", "true").lower() == "true"
    )

    # Metacognition Engine configuration (internal thought tracking)
    metacognition_enabled = os.getenv("METACOGNITION_ENABLED", "true").lower() == "true"
    metacognition_db_path = os.getenv("METACOGNITION_DB_PATH", "data/metacognition.db")
    show_thoughts_inline = os.getenv("SHOW_THOUGHTS_INLINE", "true").lower() == "true"

    # Lives & Memories system configuration (timeline branching & save states)
    lives_enabled = os.getenv("LIVES_ENABLED", "true").lower() == "true"

    # Universal Rules configuration (global directives for all personas)
    # Format: pipe-separated list of rules
    # Example: "Rule 1 | Rule 2 | Rule 3"
    universal_rules_env = os.getenv("UNIVERSAL_RULES")
    universal_rules = None
    if universal_rules_env:
        # Split by pipe and strip whitespace
        universal_rules = [
            rule.strip() for rule in universal_rules_env.split("|") if rule.strip()
        ]

    # Vision API configuration (optional)
    vision_api_key = os.getenv("VISION_API_KEY", "not-needed")
    vision_base_url = os.getenv("VISION_BASE_URL")
    vision_model = os.getenv("VISION_MODEL", "vision-model")

    # Validate environment
    if not discord_token:
        raise ValueError("DISCORD_TOKEN not found in environment")
    if not api_key:
        raise ValueError("LLM_API_KEY not found in environment")

    # Initialize AgentCore (platform-agnostic)
    agent_core = AgentCore(
        api_key=api_key,
        base_url=base_url,
        model=model,
        short_term_limit=short_term_limit,
        vector_memory_enabled=vector_memory_enabled,
        semantic_recall_limit=semantic_recall_limit,
        tools_enabled=tools_enabled,
        max_tool_iterations=max_tool_iterations,
        graph_memory_enabled=graph_memory_enabled,
        graph_db_path=graph_db_path,
        limbic_enabled=limbic_enabled,
        limbic_db_path=limbic_db_path,
        digital_pharmacy_enabled=digital_pharmacy_enabled,
        cadence_degrader_enabled=cadence_degrader_enabled,
        metacognition_enabled=metacognition_enabled,
        metacognition_db_path=metacognition_db_path,
        show_thoughts_inline=show_thoughts_inline,
        lives_enabled=lives_enabled,
        universal_rules=universal_rules,
    )

    # Initialize VisionBridge if configured
    vision_bridge = None
    if vision_base_url:
        try:
            vision_bridge = VisionBridge(
                vision_api_key=vision_api_key,
                vision_base_url=vision_base_url,
                vision_model=vision_model,
            )
            print(f"✓ Vision Bridge enabled: {vision_base_url}")
        except Exception as e:
            print(f"⚠ Vision Bridge initialization failed: {e}")
            print("  Continuing without vision support...")
    else:
        print("ℹ Vision Bridge not configured (set VISION_BASE_URL to enable)")

    # Create Discord adapter
    bot = create_discord_bot(agent_core, vision_bridge)

    # Run bot
    print("Starting Myriad Discord Adapter...")
    bot.run(discord_token)


if __name__ == "__main__":
    run_discord_adapter()

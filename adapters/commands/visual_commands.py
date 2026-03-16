"""
Visual Memory Commands - Discord interface for the Visual Memory Engine.

This module provides Discord slash commands for character visual profile management.
It wraps the platform-agnostic VisualManager with Discord-specific UI.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import io

from core.features.visual_memory import VisualManager
from adapters.commands.base import ResponseFormatter


class VisualCommands(commands.Cog):
    """Discord commands for managing character visual profiles."""

    def __init__(self, bot: commands.Bot):
        """
        Initialize Visual Commands cog.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot

        # Initialize Visual Manager (platform-agnostic engine)
        try:
            self.visual_manager = VisualManager()
            print("✅ Visual Memory Engine initialized")
        except ValueError as e:
            print(f"⚠ Visual Memory Engine initialization failed: {e}")
            self.visual_manager = None
        except ImportError as e:
            print(f"⚠ Visual Memory Engine unavailable: {e}")
            self.visual_manager = None

    async def _check_available(self, interaction: discord.Interaction) -> bool:
        """
        Check if Visual Manager is available.

        Args:
            interaction: Discord interaction

        Returns:
            True if available, False otherwise (sends error message)
        """
        if not self.visual_manager:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    "Visual Memory Engine is not available. "
                    "Ensure GEMINI_API_KEY is set and google-genai is installed."
                ),
                ephemeral=True,
            )
            return False
        return True

    @app_commands.command(
        name="visual_learn",
        description="Learn a character's appearance from a reference image",
    )
    @app_commands.describe(
        character_name="Name of the character (e.g., 'alice', 'bob')",
        image="Character reference image (PNG, JPG, WEBP, etc.)",
    )
    async def visual_learn(
        self,
        interaction: discord.Interaction,
        character_name: str,
        image: discord.Attachment,
    ):
        """
        Extract and save character visual profile from reference image.

        This command analyzes the uploaded image and generates a comprehensive
        visual description that can be used for future image generation.

        Args:
            interaction: Discord interaction
            character_name: Name/ID of the character
            image: Uploaded character reference image
        """
        if not self._check_available(interaction):
            return

        # Defer response (vision analysis takes time)
        await interaction.response.defer(ephemeral=False)

        try:
            # Validate image attachment
            if not image.content_type or not image.content_type.startswith("image/"):
                await interaction.followup.send(
                    ResponseFormatter.error("Please upload a valid image file."),
                    ephemeral=True,
                )
                return

            # Download image bytes
            image_bytes = await image.read()

            # Extract visual profile using Vision API
            visual_tags = await self.visual_manager.extract_and_save_profile(
                character_name=character_name,
                image_bytes=image_bytes,
            )

            # Send success message with extracted tags
            embed = discord.Embed(
                title=f"✓ Learned Visual Profile: {character_name}",
                description=f"**Extracted Tags:**\n{visual_tags}",
                color=discord.Color.green(),
            )
            embed.set_footer(
                text=f"Use /visual_generate to create images of {character_name}"
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Failed to extract visual profile: {str(e)}"),
                ephemeral=True,
            )

    @app_commands.command(
        name="visual_generate",
        description="Generate an image of a learned character",
    )
    @app_commands.describe(
        character_name="Name of the character to generate",
        action="Description of what the character is doing (e.g., 'standing in a forest')",
        aspect_ratio="Image aspect ratio (default: 1:1)",
    )
    @app_commands.choices(
        aspect_ratio=[
            app_commands.Choice(name="Square (1:1)", value="1:1"),
            app_commands.Choice(name="Landscape (16:9)", value="16:9"),
            app_commands.Choice(name="Portrait (9:16)", value="9:16"),
            app_commands.Choice(name="Landscape (4:3)", value="4:3"),
            app_commands.Choice(name="Portrait (3:4)", value="3:4"),
        ]
    )
    async def visual_generate(
        self,
        interaction: discord.Interaction,
        character_name: str,
        action: str,
        aspect_ratio: Optional[app_commands.Choice[str]] = None,
    ):
        """
        Generate an image of a character using their stored visual profile.

        The character must have a visual profile created via /visual_learn first.

        Args:
            interaction: Discord interaction
            character_name: Name/ID of the character
            action: Description of action/scene
            aspect_ratio: Image aspect ratio choice
        """
        if not self._check_available(interaction):
            return

        # Defer response (image generation takes time)
        await interaction.response.defer(ephemeral=False)

        try:
            # Extract aspect ratio value
            ratio = aspect_ratio.value if aspect_ratio else "1:1"

            # Generate image using Visual Manager
            image_bytes = await self.visual_manager.generate_character_image(
                character_name=character_name,
                action_prompt=action,
                aspect_ratio=ratio,
            )

            # Create Discord file attachment
            file = discord.File(
                fp=io.BytesIO(image_bytes),
                filename=f"{character_name}_{action[:20].replace(' ', '_')}.png",
            )

            # Send image with description
            embed = discord.Embed(
                title=f"Generated: {character_name}",
                description=f"**Action:** {action}",
                color=discord.Color.blue(),
            )
            embed.set_image(url=f"attachment://{file.filename}")

            await interaction.followup.send(embed=embed, file=file)

        except ValueError as e:
            # Character not found or other validation error
            await interaction.followup.send(
                ResponseFormatter.error(str(e)),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(f"Failed to generate image: {str(e)}"),
                ephemeral=True,
            )

    @app_commands.command(
        name="visual_show",
        description="Show a character's stored visual profile",
    )
    @app_commands.describe(
        character_name="Name of the character to view",
    )
    async def visual_show(
        self,
        interaction: discord.Interaction,
        character_name: str,
    ):
        """
        Display the stored visual profile for a character.

        Args:
            interaction: Discord interaction
            character_name: Name/ID of the character
        """
        if not self._check_available(interaction):
            return

        visual_tags = self.visual_manager.get_visual_profile(character_name)

        if not visual_tags:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"No visual profile found for '{character_name}'. "
                    f"Use /visual_learn to create one."
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"Visual Profile: {character_name}",
            description=f"**Tags:**\n{visual_tags}",
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="visual_list",
        description="List all characters with visual profiles",
    )
    async def visual_list(self, interaction: discord.Interaction):
        """
        List all characters that have visual profiles saved.

        Args:
            interaction: Discord interaction
        """
        if not self._check_available(interaction):
            return

        characters = self.visual_manager.list_characters()

        if not characters:
            await interaction.response.send_message(
                "No visual profiles saved yet. Use /visual_learn to create one.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Characters with Visual Profiles",
            description="\n".join(f"• {name}" for name in characters),
            color=discord.Color.blue(),
        )
        embed.set_footer(
            text=f"{len(characters)} character(s) | Use /visual_show to view details"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="visual_delete",
        description="Delete a character's visual profile",
    )
    @app_commands.describe(
        character_name="Name of the character to delete",
    )
    async def visual_delete(
        self,
        interaction: discord.Interaction,
        character_name: str,
    ):
        """
        Delete a character's stored visual profile.

        Args:
            interaction: Discord interaction
            character_name: Name/ID of the character
        """
        if not self._check_available(interaction):
            return

        deleted = self.visual_manager.delete_profile(character_name)

        if deleted:
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"Deleted visual profile for '{character_name}'"
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"No visual profile found for '{character_name}'"
                ),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """
    Setup function for loading this cog.

    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(VisualCommands(bot))

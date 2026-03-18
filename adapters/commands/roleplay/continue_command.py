"""
Continue command for Discord.

Allows the AI to continue/extend their previous response without additional user input.
"""

import discord
from discord import app_commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_continue_command(bot: "MyriadDiscordBot") -> None:
    """
    Register the /continue command.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="continue",
        description="Ask the AI to continue/extend their previous response",
    )
    async def continue_response(interaction: discord.Interaction):
        """
        Have the AI continue from their last response.

        This injects a continuation prompt that asks the AI to extend
        what they were saying without adding new user input.
        """
        # Defer immediately since we're processing a message
        await interaction.response.defer()

        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel_id)

        # Inject a continuation prompt as a user message
        continuation_prompt = "[Continue your previous response. Expand on what you were saying or add more detail.]"

        try:
            # Process the continuation request through the normal message flow
            response, generated_images = bot.agent_core.process_message(
                user_id=user_id,
                message=continuation_prompt,
                life_id=None,  # Use default life
                memory_visibility="SCOPED",
            )

            if response:
                # Send the continuation
                await interaction.followup.send(response)

                # Send any generated images
                if generated_images:
                    for image_data in generated_images:
                        file = discord.File(
                            fp=image_data["data"], filename=image_data["filename"]
                        )
                        await interaction.followup.send(file=file)
            else:
                await interaction.followup.send(
                    "❌ Failed to generate continuation. Please try again.",
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error during continuation: {str(e)}", ephemeral=True
            )

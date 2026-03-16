"""
Session Note Commands - Intelligent meta-level context injection with Discretion Engine.

Provides /note command for injecting directives into the prompt context with automatic
classification into short-term (volatile) or long-term (semantic) memory.

The Discretion Engine (LLM-based classifier) evaluates each note and routes it to:
- Short-term memory: Temporary context injection with TTL (auto-expires after N turns)
- Long-term memory: Permanent semantic storage in ChromaDB

Part of Project Myriad's meta-control toolkit.
"""

import discord
import json
from discord import app_commands
from typing import TYPE_CHECKING, Optional

from adapters.commands.base import ResponseFormatter

if TYPE_CHECKING:
    from adapters.discord_adapter import MyriadDiscordBot


def register_note_commands(bot: "MyriadDiscordBot") -> None:
    """
    Register session note commands with Discretion Engine classification.

    Args:
        bot: The Discord bot instance
    """

    @bot.tree.command(
        name="note",
        description="Add a note - AI automatically routes to short-term or long-term memory",
    )
    @app_commands.describe(
        text="The note to add (use 'clear' to remove short-term notes)"
    )
    async def set_note(interaction: discord.Interaction, text: str):
        """Set a note with automatic Discretion Engine classification."""
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer
            return

        user_id = str(interaction.user.id)

        # Check if user wants to clear short-term notes
        if text.lower().strip() in ["clear", "remove", "delete", ""]:
            cleared = bot.agent_core.session_notes.clear_note(user_id)

            if cleared:
                await interaction.followup.send(
                    ResponseFormatter.success(
                        "📝 Short-term session note cleared.\n\n"
                        "Note: Long-term facts stored in semantic memory remain."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    ResponseFormatter.warning("No active short-term note to clear."),
                    ephemeral=True,
                )
            return

        # Get active persona for context
        personas = bot.agent_core.get_active_personas(user_id)
        if not personas:
            await interaction.followup.send(
                ResponseFormatter.error(
                    "No active persona. Use `/swap <persona_id>` first."
                ),
                ephemeral=True,
            )
            return

        persona = personas[0]

        # Send note to Discretion Engine for classification
        try:
            classification_result = await _classify_note_with_discretion_engine(
                bot, text, user_id, persona.persona_id
            )
        except Exception as e:
            await interaction.followup.send(
                ResponseFormatter.error(
                    f"Discretion Engine failed to classify note: {str(e)}\n\n"
                    f"Note was not saved."
                ),
                ephemeral=True,
            )
            return

        # Route based on classification
        if classification_result["classification"] == "long_term":
            # Store in ChromaDB as semantic memory
            extracted_fact = classification_result["extracted_fact"]

            # Add to vector memory
            memory_id = f"note_{user_id}_{int(interaction.created_at.timestamp())}"
            bot.agent_core.memory_matrix.memory_repo.add_memory(
                user_id=user_id,
                origin_persona=persona.persona_id,
                role="system",
                content=f"[Fact]: {extracted_fact}",
                visibility_scope="GLOBAL",
                life_id="",
                importance_score=classification_result.get("importance_score", 7),
            )

            await interaction.followup.send(
                ResponseFormatter.success(
                    f"🧠 **Long-Term Fact Stored**\n\n"
                    f"**Original Note:** {text}\n\n"
                    f"**Extracted Fact:** {extracted_fact}\n\n"
                    f"**Reasoning:** {classification_result['reasoning']}\n\n"
                    f"**Importance Score:** {classification_result.get('importance_score', 7)}/10\n\n"
                    f"This fact has been embedded into semantic memory and will be "
                    f"recalled when contextually relevant."
                ),
                ephemeral=True,
            )

        else:  # short_term
            # Store in short-term session state with TTL
            ttl_turns = classification_result.get("ttl_turns", 5)
            extracted_note = classification_result["extracted_fact"]

            bot.agent_core.session_notes.set_note(
                user_id=user_id,
                note_text=extracted_note,
                ttl_turns=ttl_turns,
            )

            await interaction.followup.send(
                ResponseFormatter.success(
                    f"⏱️ **Short-Term Note Set**\n\n"
                    f"**Original Note:** {text}\n\n"
                    f"**Processed Note:** {extracted_note}\n\n"
                    f"**Reasoning:** {classification_result['reasoning']}\n\n"
                    f"**TTL:** {ttl_turns} conversation turns\n\n"
                    f"This note will be injected into the AI's context and auto-expire "
                    f"after {ttl_turns} messages.\n\n"
                    f"Use `/note clear` to remove it manually."
                ),
                ephemeral=True,
            )

    @bot.tree.command(
        name="note_status",
        description="Check your active short-term and long-term notes",
    )
    async def note_status(interaction: discord.Interaction):
        """Show the current note status."""
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # Interaction expired before we could defer
            return

        user_id = str(interaction.user.id)

        # Get short-term note
        short_term_note = bot.agent_core.session_notes.get_note_with_ttl(user_id)

        # Build response
        response = "📝 **Note Status**\n\n"

        if short_term_note:
            note_text, ttl = short_term_note
            preview = note_text[:200] + "..." if len(note_text) > 200 else note_text
            response += (
                f"**⏱️ Short-Term Note (Active):**\n```\n{preview}\n```\n"
                f"Remaining turns: {ttl}\n\n"
            )
        else:
            response += "**⏱️ Short-Term Note:** None\n\n"

        response += (
            "**🧠 Long-Term Facts:** Stored in semantic memory\n"
            "Use `/memory search <query>` to explore semantic memories.\n\n"
            "Use `/note clear` to remove short-term notes."
        )

        await interaction.followup.send(response, ephemeral=True)


async def _classify_note_with_discretion_engine(
    bot: "MyriadDiscordBot", note_text: str, user_id: str, persona_id: str
) -> dict:
    """
    Use the Discretion Engine (LLM) to classify a note as short-term or long-term.

    Args:
        bot: Discord bot instance
        note_text: The note text to classify
        user_id: User identifier
        persona_id: Active persona identifier

    Returns:
        Dictionary with classification result:
        {
            "classification": "short_term" | "long_term",
            "reasoning": "Brief explanation",
            "ttl_turns": 5,  # Only for short_term
            "extracted_fact": "Cleaned up version",
            "importance_score": 7  # Only for long_term (1-10)
        }
    """
    # Build Discretion Engine system prompt
    discretion_prompt = """You are the Discretion Engine for Project Myriad's memory system.

Your job is to analyze user notes and classify them as either SHORT-TERM or LONG-TERM memory.

CLASSIFICATION RULES:

SHORT-TERM (volatile, temporary context):
- Temporary physical states: "I'm injured", "I'm drunk", "I'm sleepy"
- Momentary emotions: "I'm angry right now", "Feeling sad today"
- Current tasks/goals: "Looking for a specific item", "Heading to the store"
- Scene-specific details: "It's raining outside", "The room is dark"
- Temporary social dynamics: "Avoiding eye contact", "Being sarcastic"
- TTL: Estimate how many conversation turns this remains relevant (1-20)

LONG-TERM (permanent, semantic facts):
- Core identity traits: "I have PTSD", "I'm allergic to peanuts", "I'm left-handed"
- Relationship facts: "We've been friends for 5 years", "I trust you completely"
- Hard preferences: "I hate loud noises", "I love classical music"
- Important life events: "My father died last year", "I graduated from MIT"
- Core values/beliefs: "I'm a pacifist", "Family comes first for me"
- Permanent physical traits: "I have a scar on my left arm"
- Importance Score: Rate 1-10 (1=trivial, 10=life-changing/core anchor)

RESPOND IN JSON FORMAT ONLY:
{
  "classification": "short_term" or "long_term",
  "reasoning": "Brief 1-sentence explanation",
  "ttl_turns": 5,  // Only if short_term. How many turns this stays relevant.
  "extracted_fact": "Cleaned, clear version of the note",
  "importance_score": 7  // Only if long_term. 1-10 rating.
}"""

    # Build conversation context for LLM
    messages = [
        {"role": "system", "content": discretion_prompt},
        {
            "role": "user",
            "content": f"Classify this note:\n\n{note_text}",
        },
    ]

    # Call LLM
    response = bot.agent_core.client.chat.completions.create(
        model=bot.agent_core.model,
        messages=messages,
        temperature=0.2,  # Low temperature for consistent classification
        max_tokens=200,
    )

    # Extract and parse JSON
    response_text = response.choices[0].message.content.strip()

    # Try to extract JSON from markdown code blocks if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {response_text}") from e

    # Validate required fields
    if "classification" not in result or result["classification"] not in [
        "short_term",
        "long_term",
    ]:
        raise ValueError(f"Invalid classification in result: {result}")

    if "extracted_fact" not in result:
        result["extracted_fact"] = note_text  # Fallback to original

    # Ensure proper fields based on classification
    if result["classification"] == "short_term":
        if "ttl_turns" not in result or not isinstance(result["ttl_turns"], int):
            result["ttl_turns"] = 5  # Default TTL
        # Clamp TTL to reasonable range
        result["ttl_turns"] = max(1, min(20, result["ttl_turns"]))
    else:  # long_term
        if "importance_score" not in result or not isinstance(
            result["importance_score"], int
        ):
            result["importance_score"] = 7  # Default importance
        # Clamp importance to valid range
        result["importance_score"] = max(1, min(10, result["importance_score"]))

    return result

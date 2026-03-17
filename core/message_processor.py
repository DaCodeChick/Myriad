"""
MessageProcessor - Handles message processing pipeline with tool execution and limbic respiration.

This module manages the complete message processing cycle including:
- Tool execution loop
- Limbic respiration (INHALE/EXHALE)
- Cadence degradation
- Metacognition extraction

Extracted from AgentCore as part of RDSSC Phase 3.
Refactored to use modular provider system for LLM backends.
RDSSC Phase 4: Extracted async helpers to utils/async_utils.py
"""

import re
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple

from core.features.roleplay.persona import PersonaCartridge
from core.providers.base import LLMProvider
from core.tool_registry import ToolRegistry, parse_tool_call, format_tool_response
from core.logger import get_logger
from core.features.roleplay.limbic_engine import LimbicEngine
from core.features.roleplay.metacognition_engine import MetacognitionEngine
from core.features.roleplay.mode_manager import ModeManager
from database.user_preferences import UserPreferences
from core.features.roleplay.cadence_degrader import CadenceDegrader
from core.utils.async_utils import run_async_safe

if TYPE_CHECKING:
    from core.features.roleplay.user_masks import UserMaskManager
    from core.features.roleplay.session_notes import SessionNotesManager


class MessageProcessor:
    """
    Processes messages through the complete AI pipeline.

    PROCESSING PIPELINE:
    1. Preprocess message (vision injection, etc.)
    2. Tool execution loop (up to max_tool_iterations)
    3. Limbic respiration EXHALE phase (metabolic decay)
    4. Metacognition extraction (strip <thought> tags FIRST)
    5. Cadence degradation (mutate spoken text only, after tags removed)
    """

    def __init__(
        self,
        provider: LLMProvider,
        max_tool_iterations: int = 5,
        limbic_engine: Optional[LimbicEngine] = None,
        metacognition_engine: Optional[MetacognitionEngine] = None,
        cadence_degrader: Optional[CadenceDegrader] = None,
        mode_manager: Optional[ModeManager] = None,
        user_mask_manager: Optional["UserMaskManager"] = None,
        user_preferences_manager: Optional[UserPreferences] = None,
        session_notes: Optional["SessionNotesManager"] = None,
    ):
        """
        Initialize the message processor.

        Args:
            provider: LLM provider instance (OpenAI, Gemini, etc.)
            max_tool_iterations: Maximum tool call iterations per message
            limbic_engine: Optional limbic system for emotional processing
            metacognition_engine: Optional metacognition system for thought tracking
            cadence_degrader: Optional cadence degrader for text post-processing
            mode_manager: Optional mode override manager
            user_mask_manager: Optional user mask manager for relationship overrides
            user_preferences_manager: Optional user preferences manager for degradation profiles
            session_notes: Optional session notes manager for TTL tracking
        """
        self.provider = provider
        self.max_tool_iterations = max_tool_iterations
        self.limbic_engine = limbic_engine
        self.metacognition_engine = metacognition_engine
        self.cadence_degrader = cadence_degrader
        self.mode_manager = mode_manager
        self.user_mask_manager = user_mask_manager
        self.user_preferences_manager = user_preferences_manager
        self.session_notes = session_notes

    def get_pending_images(
        self, tool_registry: Optional[ToolRegistry]
    ) -> List[Tuple[bytes, str]]:
        """
        Retrieve any images generated during the last message processing.

        Args:
            tool_registry: Tool registry that may contain pending images

        Returns:
            List of (image_bytes, mime_type) tuples
        """
        if tool_registry and hasattr(tool_registry, "get_pending_images"):
            return tool_registry.get_pending_images()
        return []

    def process(
        self,
        messages: List[Dict[str, str]],
        persona: PersonaCartridge,
        user_id: str,
        tool_registry: Optional[ToolRegistry] = None,
        on_message_saved: Optional[callable] = None,
        user_preferences: Optional[Dict[str, bool]] = None,
        image_data: Optional[List[Tuple[bytes, str]]] = None,
    ) -> Optional[str]:
        """
        Process messages through the complete AI pipeline.

        Args:
            messages: Conversation context messages
            persona: Current active persona
            user_id: User identifier for limbic/metacognition processing
            tool_registry: Optional tool registry for function calling
            on_message_saved: Optional callback for saving messages (assistant/tool messages)
                            Signature: on_message_saved(role: str, content: str)
            user_preferences: Optional user preference flags
            image_data: Optional list of (image_bytes, mime_type) tuples for vision

        Returns:
            Final AI response string, or None on error
        """
        # Default preferences if not provided
        if user_preferences is None:
            user_preferences = {
                "limbic_enabled": True,
                "cadence_degrader_enabled": True,
                "metacognition_enabled": True,
                "show_thoughts_inline": True,
            }

        # Check for mode overrides
        mode_override = None
        if self.mode_manager:
            mode_override = self.mode_manager.get_mode_override(user_id)

            # Apply mode overrides to preferences
            if mode_override.disable_limbic:
                user_preferences["limbic_enabled"] = False
            if mode_override.disable_cadence:
                user_preferences["cadence_degrader_enabled"] = False
            if mode_override.disable_metacognition:
                user_preferences["metacognition_enabled"] = False

        # Execute tool loop and get final response
        final_response = self._execute_tool_loop(
            messages, persona, tool_registry, on_message_saved, image_data
        )

        if not final_response:
            return None

        # Apply EXHALE phase (metabolic decay) - check user preference
        if user_preferences.get("limbic_enabled", True):
            self._apply_limbic_exhale(user_id, persona)

        # CRITICAL: Extract metacognition FIRST (before degradation)
        # This prevents cadence degrader from mutating XML tags like <thought>
        if user_preferences.get("metacognition_enabled", True):
            final_response = self._extract_metacognition(
                final_response, user_id, persona.persona_id, user_preferences
            )

        # Apply cadence degradation AFTER tag stripping
        # This ensures degradation only affects the spoken text, not system tags
        # Skip degradation for narrator personas (they should speak clearly)
        if (
            user_preferences.get("cadence_degrader_enabled", True)
            and not persona.is_narrator
        ):
            final_response = self._apply_cadence_degradation(
                final_response, user_id, persona.persona_id, user_preferences
            )

        # Decrement session note TTL (after successful response generation)
        if self.session_notes:
            self.session_notes.decrement_ttl(user_id)

        return final_response

    def _execute_tool_loop(
        self,
        messages: List[Dict[str, str]],
        persona: PersonaCartridge,
        tool_registry: Optional[ToolRegistry],
        on_message_saved: Optional[callable],
        image_data: Optional[List[Tuple[bytes, str]]] = None,
    ) -> Optional[str]:
        """
        Execute the tool execution loop.

        TOOL EXECUTION LOOP:
        1. LLM responds
        2. If response is a tool call (JSON format), execute the tool
        3. Inject tool result back into conversation
        4. LLM reads result and responds to user
        5. Repeat up to max_tool_iterations times

        Args:
            messages: Conversation context (will be modified with tool calls)
            persona: Current persona for temperature/max_tokens
            tool_registry: Optional tool registry
            on_message_saved: Optional callback for saving messages
            image_data: Optional list of (image_bytes, mime_type) tuples for vision

        Returns:
            Final response string, or None on error
        """
        tool_iterations = 0

        while tool_iterations < self.max_tool_iterations:
            try:
                # Call LLM API via provider (async)
                assistant_message = run_async_safe(
                    self.provider.generate(
                        messages=messages,
                        temperature=persona.temperature,
                        max_tokens=persona.max_tokens,
                        image_data=image_data if tool_iterations == 0 else None,
                    )
                )

                if not assistant_message:
                    return None

                # Log response from LLM (strip <thought> tags to avoid duplicate with thought logging)
                logger = get_logger()
                response_without_thoughts = re.sub(
                    r"<thought>.*?</thought>\s*", "", assistant_message, flags=re.DOTALL
                ).strip()

                # Only log if there's actual content after stripping thoughts
                if response_without_thoughts:
                    logger.log_brain_response(
                        persona.persona_id, response_without_thoughts
                    )

                # Check if this is a tool call
                if tool_registry:
                    tool_call = parse_tool_call(assistant_message)

                    if tool_call:
                        # Execute tool and continue loop
                        tool_iterations += 1
                        tool_name = tool_call["tool"]
                        tool_args = tool_call["arguments"]

                        print(f"[Tool Call {tool_iterations}] {tool_name}({tool_args})")

                        # Execute the tool (async if available)
                        # Check if this is the generate_image tool which needs async
                        if tool_name == "generate_image" and hasattr(
                            tool_registry, "execute_tool_async"
                        ):
                            # Run async tool using helper
                            result = run_async_safe(
                                tool_registry.execute_tool_async(tool_name, tool_args)
                            )
                        else:
                            # Use sync execution for other tools
                            result = tool_registry.execute_tool(tool_name, tool_args)

                        tool_response_text = format_tool_response(tool_name, result)

                        print(f"[Tool Result] {result}")

                        # Add tool call and result to conversation
                        messages.append(
                            {"role": "assistant", "content": assistant_message}
                        )
                        messages.append({"role": "user", "content": tool_response_text})

                        # Save to memory if callback provided
                        if on_message_saved:
                            on_message_saved("assistant", assistant_message)
                            on_message_saved("user", tool_response_text)

                        # Continue loop
                        continue

                # Not a tool call - this is the final response
                return assistant_message

            except Exception as e:
                print(f"Error calling LLM API: {e}")
                return None

        # Exhausted iterations without final response
        return "I apologize, but I encountered an issue processing your request."

    def _apply_limbic_exhale(self, user_id: str, persona: "PersonaCartridge") -> None:
        """
        Apply EXHALE phase - metabolic decay.

        Apply 10% decay toward baseline to prevent indefinite emotional extremes.
        Uses persona-specific baseline if defined, with relationship overrides applied.

        Args:
            user_id: User identifier
            persona: Current persona (for accessing limbic baseline and relationships)
        """
        if self.limbic_engine:
            # Check for relationship limbic baseline override
            # Special handling: If no mask is active, check for "@user" relationship
            effective_baseline = persona.limbic_baseline
            if self.user_mask_manager:
                user_mask = self.user_mask_manager.get_active_mask(user_id)
                target_id = user_mask.persona_id if user_mask else "@user"

                active_relationship = persona.get_relationship_override(target_id)
                if active_relationship and active_relationship.limbic_baseline_override:
                    # Merge relationship override with base baseline
                    effective_baseline = (
                        persona.limbic_baseline.copy()
                        if persona.limbic_baseline
                        else {}
                    )
                    effective_baseline.update(
                        active_relationship.limbic_baseline_override
                    )

            self.limbic_engine.apply_metabolic_decay(
                user_id=user_id,
                persona_id=persona.persona_id,
                persona_baseline=effective_baseline,
            )

    def _apply_cadence_degradation(
        self,
        response: str,
        user_id: str,
        persona_id: str,
        user_preferences: Dict,
    ) -> str:
        """
        Apply cadence degradation based on extreme limbic states.

        Args:
            response: Original response text
            user_id: User identifier
            persona_id: Persona identifier
            user_preferences: User preferences dict

        Returns:
            Degraded response text (or original if no degradation needed)
        """
        if not self.cadence_degrader or not self.limbic_engine:
            return response

        limbic_state = self.limbic_engine.get_state(
            user_id=user_id, persona_id=persona_id
        )

        if limbic_state and self.cadence_degrader.should_degrade(limbic_state):
            # Load degradation profile
            if self.user_preferences_manager:
                degradation_profile = (
                    self.user_preferences_manager.get_degradation_profile(
                        user_id, persona_id, profile_name="subtle"
                    )
                )
            else:
                # Fallback to default profile
                degradation_profile = {
                    "vowel_stretch_enabled": True,
                    "panic_effects_enabled": True,
                    "sedation_effects_enabled": True,
                    "vowel_stretch_base_chance": 0.01,
                    "vowel_stretch_scale_factor": 0.057,
                    "vowel_stretch_min_word_length": 4,
                    "vowel_stretch_max_repeats": 2,
                    "panic_stutter_base_chance": 0.05,
                    "panic_stutter_scale_factor": 0.10,
                    "panic_caps_base_chance": 0.03,
                    "panic_caps_scale_factor": 0.07,
                    "panic_min_word_length": 3,
                    "sedation_ellipsis_chance": 0.3,
                }

            return self.cadence_degrader.degrade(
                response, limbic_state, degradation_profile
            )

        return response

    def _extract_metacognition(
        self,
        response: str,
        user_id: str,
        persona_id: str,
        user_preferences: Dict[str, bool],
    ) -> str:
        """
        Extract and process internal thoughts from response.

        Extracts <thought>...</thought> tags (or [thought]...[end thought] as fallback),
        saves to database, and either:
        - Formats inline with emoji (if show_thoughts_inline=True in user_preferences)
        - Strips from response and prints to terminal (if show_thoughts_inline=False)

        Uses non-greedy regex matching with DOTALL to handle multi-line thought blocks.
        Processes ALL thought blocks in the response, not just the first one.

        Args:
            response: Response text potentially containing thought tags
            user_id: User identifier
            persona_id: Persona identifier
            user_preferences: User preference flags

        Returns:
            Response with thoughts formatted or stripped
        """
        if not self.metacognition_engine:
            return response

        # First, normalize any incorrect formats to the correct format
        # Handle [thought]...[end thought] -> <thought>...</thought>
        response = re.sub(
            r"\[thought\](.*?)\[end thought\]",
            r"<thought>\1</thought>",
            response,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Handle [thought]...[/thought] -> <thought>...</thought>
        response = re.sub(
            r"\[thought\](.*?)\[/thought\]",
            r"<thought>\1</thought>",
            response,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Extract ALL thought blocks using non-greedy regex (handles multi-line)
        thought_matches = re.finditer(r"<thought>(.*?)</thought>", response, re.DOTALL)

        # Collect all thoughts for saving
        thoughts = []
        for match in thought_matches:
            thought_content = match.group(1).strip()
            if thought_content:  # Skip empty thoughts
                thoughts.append(thought_content)

        # Save all thoughts to database
        for thought_content in thoughts:
            self.metacognition_engine.save_thought(
                user_id=user_id,
                persona_id=persona_id,
                thought=thought_content,
            )

        # Format or strip thoughts based on user preference
        show_inline = user_preferences.get("show_thoughts_inline", False)
        if show_inline and thoughts:
            # Display thoughts inline in italics with emoji
            # Combine multiple thoughts into one formatted block
            combined_thoughts = "\n".join(thoughts)
            formatted_thought = f"*💭 [Thought: {combined_thoughts}]*\n\n"

            # Replace ALL thought tags with the formatted version
            # Use a lambda to replace only the first occurrence with formatted text,
            # and remove subsequent ones to avoid duplication
            first_replacement = True

            def replace_func(match):
                nonlocal first_replacement
                if first_replacement:
                    first_replacement = False
                    return formatted_thought
                return ""

            response = re.sub(
                r"<thought>.*?</thought>\s*",
                replace_func,
                response,
                flags=re.DOTALL,
            )
        else:
            # Strip ALL thought tags from response (terminal-only mode)
            response = re.sub(
                r"<thought>.*?</thought>\s*", "", response, flags=re.DOTALL
            )

            # Log all thoughts using the new logger
            logger = get_logger()
            for thought_content in thoughts:
                logger.log_thought(persona_id, thought_content)

        # Clean up any orphaned tags (shouldn't happen, but safety check)
        response = response.replace("<thought>", "").replace("</thought>", "")
        response = (
            response.replace("[thought]", "")
            .replace("[end thought]", "")
            .replace("[/thought]", "")
        )

        return response

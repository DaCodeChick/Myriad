"""
MessageProcessor - Handles message processing pipeline with tool execution and limbic respiration.

This module manages the complete message processing cycle including:
- Tool execution loop
- Limbic respiration (INHALE/EXHALE)
- Cadence degradation
- Metacognition extraction

Extracted from AgentCore as part of RDSSC Phase 3.
"""

import re
from typing import List, Dict, Optional
from openai import OpenAI

from core.persona_loader import PersonaCartridge
from core.tool_registry import ToolRegistry, parse_tool_call, format_tool_response
from database.limbic_engine import LimbicEngine
from database.metacognition_engine import MetacognitionEngine
from core.cadence_degrader import CadenceDegrader


class MessageProcessor:
    """
    Processes messages through the complete AI pipeline.

    PROCESSING PIPELINE:
    1. Preprocess message (vision injection, etc.)
    2. Tool execution loop (up to max_tool_iterations)
    3. Limbic respiration EXHALE phase (metabolic decay)
    4. Cadence degradation (text post-processing)
    5. Metacognition extraction (internal thought processing)
    """

    def __init__(
        self,
        client: OpenAI,
        model: str,
        max_tool_iterations: int = 5,
        limbic_engine: Optional[LimbicEngine] = None,
        metacognition_engine: Optional[MetacognitionEngine] = None,
        cadence_degrader: Optional[CadenceDegrader] = None,
        show_thoughts_inline: bool = True,
    ):
        """
        Initialize the message processor.

        Args:
            client: OpenAI-compatible API client
            model: Model name to use
            max_tool_iterations: Maximum tool call iterations per message
            limbic_engine: Optional limbic system for emotional processing
            metacognition_engine: Optional metacognition system for thought tracking
            cadence_degrader: Optional cadence degrader for text post-processing
            show_thoughts_inline: Display thoughts inline vs terminal-only
        """
        self.client = client
        self.model = model
        self.max_tool_iterations = max_tool_iterations
        self.limbic_engine = limbic_engine
        self.metacognition_engine = metacognition_engine
        self.cadence_degrader = cadence_degrader
        self.show_thoughts_inline = show_thoughts_inline

    def process(
        self,
        messages: List[Dict[str, str]],
        persona: PersonaCartridge,
        user_id: str,
        tool_registry: Optional[ToolRegistry] = None,
        on_message_saved: Optional[callable] = None,
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

        Returns:
            Final AI response string, or None on error
        """
        # Execute tool loop and get final response
        final_response = self._execute_tool_loop(
            messages, persona, tool_registry, on_message_saved
        )

        if not final_response:
            return None

        # Apply EXHALE phase (metabolic decay)
        self._apply_limbic_exhale(user_id, persona.persona_id)

        # Apply cadence degradation
        final_response = self._apply_cadence_degradation(
            final_response, user_id, persona.persona_id
        )

        # Extract and process metacognition
        final_response = self._extract_metacognition(
            final_response, user_id, persona.persona_id
        )

        return final_response

    def _execute_tool_loop(
        self,
        messages: List[Dict[str, str]],
        persona: PersonaCartridge,
        tool_registry: Optional[ToolRegistry],
        on_message_saved: Optional[callable],
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

        Returns:
            Final response string, or None on error
        """
        tool_iterations = 0

        while tool_iterations < self.max_tool_iterations:
            try:
                # Call LLM API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=persona.temperature,
                    max_tokens=persona.max_tokens,
                )

                # Extract response text
                assistant_message = response.choices[0].message.content

                if not assistant_message:
                    return None

                # Check if this is a tool call
                if tool_registry:
                    tool_call = parse_tool_call(assistant_message)

                    if tool_call:
                        # Execute tool and continue loop
                        tool_iterations += 1
                        tool_name = tool_call["tool"]
                        tool_args = tool_call["arguments"]

                        print(f"[Tool Call {tool_iterations}] {tool_name}({tool_args})")

                        # Execute the tool
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

    def _apply_limbic_exhale(self, user_id: str, persona_id: str):
        """
        Apply EXHALE phase - metabolic decay.

        Apply 10% decay toward baseline (0.5) to prevent indefinite emotional extremes.
        """
        if self.limbic_engine:
            self.limbic_engine.apply_metabolic_decay(
                user_id=user_id, persona_id=persona_id
            )

    def _apply_cadence_degradation(
        self, response: str, user_id: str, persona_id: str
    ) -> str:
        """
        Apply cadence degradation based on extreme limbic states.

        Args:
            response: Original response text
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Degraded response text (or original if no degradation needed)
        """
        if not self.cadence_degrader or not self.limbic_engine:
            return response

        limbic_state = self.limbic_engine.get_state(
            user_id=user_id, persona_id=persona_id
        )

        if limbic_state and self.cadence_degrader.should_degrade(limbic_state):
            return self.cadence_degrader.degrade(response, limbic_state)

        return response

    def _extract_metacognition(
        self, response: str, user_id: str, persona_id: str
    ) -> str:
        """
        Extract and process internal thoughts from response.

        Extracts <thought>...</thought> tags, saves to database, and either:
        - Formats inline with emoji (if show_thoughts_inline=True)
        - Strips from response and prints to terminal (if show_thoughts_inline=False)

        Args:
            response: Response text potentially containing thought tags
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Response with thoughts formatted or stripped
        """
        if not self.metacognition_engine:
            return response

        # Extract thought using regex (non-greedy match with DOTALL for multiline)
        thought_match = re.search(r"<thought>(.*?)</thought>", response, re.DOTALL)

        if thought_match:
            thought_content = thought_match.group(1).strip()

            # Save thought to database
            self.metacognition_engine.save_thought(
                user_id=user_id,
                persona_id=persona_id,
                thought=thought_content,
            )

            # Format or strip thought based on display mode
            if self.show_thoughts_inline:
                # Display thought inline in italics with emoji
                formatted_thought = f"*💭 [Thought: {thought_content}]*\n\n"
                response = re.sub(
                    r"<thought>.*?</thought>\s*",
                    formatted_thought,
                    response,
                    flags=re.DOTALL,
                )
            else:
                # Strip thought from response (terminal-only mode)
                response = re.sub(
                    r"<thought>.*?</thought>\s*", "", response, flags=re.DOTALL
                )
                # Print thought to terminal in yellow
                print(f"\033[93m💭 [Hidden Thought]: {thought_content}\033[0m")

        # Clean up any orphaned tags (shouldn't happen, but safety check)
        response = response.replace("<thought>", "").replace("</thought>", "")

        return response

"""
AgentCore - The platform-agnostic intelligence engine for Project Myriad.

This module is the central brain of the system. It:
1. Manages persona switching and state
2. Handles memory injection via the Automated Discretion Engine
3. Communicates with the LLM API
4. Processes messages and generates responses
5. Executes tool calls (function calling)

CRITICAL: This module must NEVER import discord or any platform-specific code.
It operates purely on strings and data structures.
"""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI

from database.memory_matrix import MemoryMatrix
from core.persona_loader import PersonaLoader, PersonaCartridge
from core.tool_registry import ToolRegistry, parse_tool_call, format_tool_response


class AgentCore:
    """
    The platform-agnostic AI engine.

    This class is the core intelligence that can be adapted to any frontend
    (Discord, Telegram, CLI, web interface, etc.)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        short_term_limit: int = 10,
        db_path: str = "data/myriad_state.db",
        personas_dir: str = "personas",
        vector_memory_enabled: bool = True,
        semantic_recall_limit: int = 5,
        tools_enabled: bool = True,
        max_tool_iterations: int = 5,
    ):
        """
        Initialize the AgentCore.

        Args:
            api_key: OpenAI API key (or compatible API)
            base_url: LLM API base URL (allows pointing to OpenRouter, local, etc.)
            model: Model name to use
            short_term_limit: Number of recent messages for immediate conversation context (default: 10)
            db_path: Path to SQLite database
            personas_dir: Directory containing persona JSON files
            vector_memory_enabled: Enable semantic vector memory (default: True)
            semantic_recall_limit: Number of semantic memories to recall from long-term storage (default: 5)
            tools_enabled: Enable tool use / function calling (default: True)
            max_tool_iterations: Maximum number of tool calls in a single response cycle (default: 5)
        """
        # LLM Client
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.short_term_limit = short_term_limit
        self.semantic_recall_limit = semantic_recall_limit
        self.tools_enabled = tools_enabled
        self.max_tool_iterations = max_tool_iterations

        # Core Systems
        self.memory_matrix = MemoryMatrix(
            db_path=db_path, vector_memory_enabled=vector_memory_enabled
        )
        self.persona_loader = PersonaLoader(personas_dir=personas_dir)

        # Tool Registry
        self.tool_registry = ToolRegistry() if tools_enabled else None

    # ========================
    # PERSONA MANAGEMENT
    # ========================

    def get_active_persona(self, user_id: str) -> Optional[PersonaCartridge]:
        """
        Get the currently active persona for a user.

        Args:
            user_id: Unique user identifier (platform-agnostic)

        Returns:
            PersonaCartridge if user has an active persona, None otherwise
        """
        persona_id = self.memory_matrix.get_active_persona(user_id)

        if not persona_id:
            return None

        return self.persona_loader.get_persona(persona_id)

    def switch_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Switch a user's active persona.

        Args:
            user_id: Unique user identifier
            persona_id: The persona to switch to

        Returns:
            True if successful, False if persona doesn't exist
        """
        # Verify persona exists
        persona = self.persona_loader.get_persona(persona_id)
        if not persona:
            return False

        # Update user state
        self.memory_matrix.set_active_persona(user_id, persona_id)
        return True

    def list_personas(self) -> List[str]:
        """
        List all available persona IDs.

        Returns:
            List of persona_id strings
        """
        return self.persona_loader.list_available_personas()

    # ========================
    # MEMORY MANAGEMENT
    # ========================

    def _build_conversation_context(
        self,
        user_id: str,
        persona: PersonaCartridge,
        current_message: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the conversation context for LLM injection using Hybrid Memory Architecture.

        MEMORY STRUCTURE (in order):
        1. System Prompt (persona + rules of engagement)
        2. Long-Term Semantic Memory (from ChromaDB - semantically relevant past conversations)
        3. Short-Term Chronological Memory (last N messages - immediate conversation flow)

        The Automated Discretion Engine filters both memory types by:
        - visibility_scope = 'GLOBAL' (shared across all personas), OR
        - origin_persona = current persona (isolated to this persona)

        Args:
            user_id: User identifier
            persona: Current active persona
            current_message: Optional current user message for semantic search

        Returns:
            List of messages in OpenAI chat format
        """
        # ========================
        # 1. SYSTEM PROMPT
        # ========================
        system_content = persona.system_prompt

        if persona.rules_of_engagement:
            # Append rules as a structured section
            rules_section = "\n\n## RULES OF ENGAGEMENT:\n" + "\n".join(
                f"- {rule}" for rule in persona.rules_of_engagement
            )
            system_content += rules_section

        # Inject tool definitions if tools are enabled
        if self.tools_enabled and self.tool_registry:
            tool_definitions = self.tool_registry.get_tool_definitions_text()
            if tool_definitions:
                system_content += tool_definitions

        # Start with system prompt
        messages = [{"role": "system", "content": system_content}]

        # ========================
        # 2. LONG-TERM SEMANTIC MEMORY (ChromaDB)
        # ========================
        # Search for semantically similar memories from the PAST (excluding recent short-term window)
        if current_message and self.memory_matrix.vector_memory_enabled:
            semantic_memories = self.memory_matrix.search_semantic_memories(
                user_id=user_id,
                current_persona=persona.persona_id,
                query=current_message,
                limit=self.semantic_recall_limit,
            )

            # If we found relevant long-term memories, inject them
            if semantic_memories:
                recalled_context = "[Recalled Long-Term Context: Semantically relevant memories from past conversations]\n\n"
                for i, memory in enumerate(semantic_memories, 1):
                    metadata = memory.get("metadata", {})
                    content = memory.get("content", "")
                    role = metadata.get("role", "unknown")
                    timestamp = metadata.get("timestamp", "unknown")

                    recalled_context += (
                        f"{i}. [{role.upper()} - {timestamp}]: {content}\n\n"
                    )

                recalled_context += "[End of Recalled Context]\n"

                # Add as a system message after the main system prompt
                messages.append({"role": "system", "content": recalled_context})

        # ========================
        # 3. SHORT-TERM CHRONOLOGICAL MEMORY (Last N messages)
        # ========================
        # Retrieve the last N messages in chronological order (immediate conversation flow)
        short_term_memories = self.memory_matrix.get_context_memories(
            user_id=user_id,
            current_persona=persona.persona_id,
            limit=self.short_term_limit,
        )

        # Convert short-term memories to OpenAI format (exact chronological order)
        for memory in short_term_memories:
            messages.append({"role": memory["role"], "content": memory["content"]})

        return messages

    def _save_message_to_memory(
        self,
        user_id: str,
        persona_id: str,
        role: str,
        content: str,
        visibility: str = "ISOLATED",
    ):
        """
        Save a message to the memory matrix.

        Args:
            user_id: User identifier
            persona_id: The persona that originated this memory
            role: 'user', 'assistant', or 'system'
            content: Message content
            visibility: 'GLOBAL' or 'ISOLATED' (default: ISOLATED)
        """
        self.memory_matrix.add_memory(
            user_id=user_id,
            origin_persona=persona_id,
            role=role,
            content=content,
            visibility_scope=visibility,
        )

    # ========================
    # CORE INTELLIGENCE
    # ========================

    def process_message(
        self,
        user_id: str,
        message: str,
        memory_visibility: str = "ISOLATED",
        vision_description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Process a user message and generate a response.

        This is the main entry point for the AI engine with Tool Execution Loop.

        TOOL EXECUTION LOOP:
        1. LLM responds
        2. If response is a tool call (JSON format), execute the tool
        3. Inject tool result back into conversation
        4. LLM reads result and responds to user
        5. Repeat up to max_tool_iterations times

        Args:
            user_id: Unique user identifier
            message: The user's message text
            memory_visibility: Visibility scope for this conversation
                             ('GLOBAL' for shared memories, 'ISOLATED' for persona-specific)
            vision_description: Optional vision model description to inject into context

        Returns:
            AI response string, or None if no active persona
        """
        # Get active persona
        persona = self.get_active_persona(user_id)

        if not persona:
            return None

        # Update user interaction timestamp
        self.memory_matrix.update_user_interaction(user_id)

        # If vision description is provided, prepend it to the message
        full_message = message
        if vision_description:
            vision_injection = f"[System: The user just uploaded an image showing: {vision_description}]\n\n{message}"
            full_message = vision_injection

        # Save user message to memory (with vision description if present)
        self._save_message_to_memory(
            user_id=user_id,
            persona_id=persona.persona_id,
            role="user",
            content=full_message,
            visibility=memory_visibility,
        )

        # Build conversation context with memory injection (pass current message for semantic search)
        messages = self._build_conversation_context(
            user_id, persona, current_message=message
        )

        # Add current message (use full_message with vision injection if present)
        messages.append({"role": "user", "content": full_message})

        # ========================
        # TOOL EXECUTION LOOP
        # ========================
        tool_iterations = 0
        final_response = None

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
                if self.tools_enabled and self.tool_registry:
                    tool_call = parse_tool_call(assistant_message)

                    if tool_call:
                        # This is a tool call! Execute it
                        tool_iterations += 1

                        tool_name = tool_call["tool"]
                        tool_args = tool_call["arguments"]

                        print(f"[Tool Call {tool_iterations}] {tool_name}({tool_args})")

                        # Execute the tool
                        result = self.tool_registry.execute_tool(tool_name, tool_args)

                        # Format the tool response
                        tool_response_text = format_tool_response(tool_name, result)

                        print(f"[Tool Result] {result}")

                        # Add tool call and result to conversation history
                        messages.append(
                            {"role": "assistant", "content": assistant_message}
                        )
                        messages.append({"role": "user", "content": tool_response_text})

                        # Save tool call and result to memory
                        self._save_message_to_memory(
                            user_id=user_id,
                            persona_id=persona.persona_id,
                            role="assistant",
                            content=assistant_message,
                            visibility=memory_visibility,
                        )

                        self._save_message_to_memory(
                            user_id=user_id,
                            persona_id=persona.persona_id,
                            role="user",
                            content=tool_response_text,
                            visibility=memory_visibility,
                        )

                        # Loop back to let LLM read the result and respond
                        continue

                # Not a tool call - this is the final response
                final_response = assistant_message
                break

            except Exception as e:
                print(f"Error calling LLM API: {e}")
                return None

        # If we exhausted iterations without a final response, use last message
        if final_response is None:
            final_response = (
                "I apologize, but I encountered an issue processing your request."
            )

        # Save final assistant response to memory
        self._save_message_to_memory(
            user_id=user_id,
            persona_id=persona.persona_id,
            role="assistant",
            content=final_response,
            visibility=memory_visibility,
        )

        return final_response

    # ========================
    # UTILITY METHODS
    # ========================

    def clear_user_memory(self, user_id: str, persona_id: Optional[str] = None):
        """
        Clear memories for a user.

        Args:
            user_id: User identifier
            persona_id: If provided, only clear memories from this persona.
                       If None, clear ALL memories.
        """
        self.memory_matrix.clear_user_memories(user_id, persona_id)

    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with memory stats
        """
        all_memories = self.memory_matrix.get_all_memories_for_user(user_id)

        global_count = sum(1 for m in all_memories if m["visibility_scope"] == "GLOBAL")
        isolated_count = sum(
            1 for m in all_memories if m["visibility_scope"] == "ISOLATED"
        )

        return {
            "total_memories": len(all_memories),
            "global_memories": global_count,
            "isolated_memories": isolated_count,
            "active_persona": self.memory_matrix.get_active_persona(user_id),
        }

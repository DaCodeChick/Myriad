"""
AgentCore - The platform-agnostic intelligence engine for Project Myriad.

This module is the central brain of the system. It:
1. Manages persona switching and state
2. Handles memory injection via the Automated Discretion Engine
3. Communicates with the LLM API
4. Processes messages and generates responses

CRITICAL: This module must NEVER import discord or any platform-specific code.
It operates purely on strings and data structures.
"""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI

from database.memory_matrix import MemoryMatrix
from core.persona_loader import PersonaLoader, PersonaCartridge


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
        memory_limit: int = 50,
        db_path: str = "database/myriad_state.db",
        personas_dir: str = "personas",
    ):
        """
        Initialize the AgentCore.

        Args:
            api_key: OpenAI API key (or compatible API)
            base_url: LLM API base URL (allows pointing to OpenRouter, local, etc.)
            model: Model name to use
            memory_limit: Maximum memories to inject into context
            db_path: Path to SQLite database
            personas_dir: Directory containing persona JSON files
        """
        # LLM Client
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.memory_limit = memory_limit

        # Core Systems
        self.memory_matrix = MemoryMatrix(db_path=db_path)
        self.persona_loader = PersonaLoader(personas_dir=personas_dir)

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
        self, user_id: str, persona: PersonaCartridge
    ) -> List[Dict[str, str]]:
        """
        Build the conversation context for LLM injection using the Automated Discretion Engine.

        Retrieves memories where:
        - visibility_scope = 'GLOBAL' (shared hive-mind), OR
        - origin_persona = current persona (isolated memories)

        Args:
            user_id: User identifier
            persona: Current active persona

        Returns:
            List of messages in OpenAI chat format
        """
        # Build system prompt with rules of engagement if present
        system_content = persona.system_prompt

        if persona.rules_of_engagement:
            # Append rules as a structured section
            rules_section = "\n\n## RULES OF ENGAGEMENT:\n" + "\n".join(
                f"- {rule}" for rule in persona.rules_of_engagement
            )
            system_content += rules_section

        # Start with system prompt
        messages = [{"role": "system", "content": system_content}]

        # Retrieve filtered memories using the Discretion Engine
        memories = self.memory_matrix.get_context_memories(
            user_id=user_id, current_persona=persona.persona_id, limit=self.memory_limit
        )

        # Convert memories to OpenAI format
        for memory in memories:
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
        self, user_id: str, message: str, memory_visibility: str = "ISOLATED"
    ) -> Optional[str]:
        """
        Process a user message and generate a response.

        This is the main entry point for the AI engine.

        Args:
            user_id: Unique user identifier
            message: The user's message text
            memory_visibility: Visibility scope for this conversation
                             ('GLOBAL' for shared memories, 'ISOLATED' for persona-specific)

        Returns:
            AI response string, or None if no active persona
        """
        # Get active persona
        persona = self.get_active_persona(user_id)

        if not persona:
            return None

        # Update user interaction timestamp
        self.memory_matrix.update_user_interaction(user_id)

        # Save user message to memory
        self._save_message_to_memory(
            user_id=user_id,
            persona_id=persona.persona_id,
            role="user",
            content=message,
            visibility=memory_visibility,
        )

        # Build conversation context with memory injection
        messages = self._build_conversation_context(user_id, persona)

        # Add current message (already in memory, but needed for API call)
        messages.append({"role": "user", "content": message})

        # Call LLM API
        try:
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

            # Save assistant response to memory
            self._save_message_to_memory(
                user_id=user_id,
                persona_id=persona.persona_id,
                role="assistant",
                content=assistant_message,
                visibility=memory_visibility,
            )

            return assistant_message

        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return None

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

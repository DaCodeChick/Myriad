"""
ConversationContextBuilder - Builds conversation context for LLM injection.

This module handles the complex task of assembling conversation context using
the Hybrid Memory Architecture, including system prompts, limbic state, knowledge
graph, semantic memories, and short-term chronological memories.

Extracted from AgentCore as part of RDSSC Phase 3.
"""

from typing import List, Dict, Optional

from core.persona_loader import PersonaCartridge
from database.memory_matrix import MemoryMatrix
from database.graph_memory import GraphMemory
from database.limbic_engine import LimbicEngine
from database.limbic_modifiers import DigitalPharmacy
from database.metacognition_engine import MetacognitionEngine
from database.mode_manager import ModeManager
from core.tool_registry import ToolRegistry


class ConversationContextBuilder:
    """
    Builds conversation context using the Hybrid Memory Architecture.

    MEMORY STRUCTURE (in order):
    1. System Prompt (persona + rules of engagement + tool definitions)
    2. Limbic State Context (INHALE - first-person somatic emotional state)
    3. Substance Modifier (Digital Pharmacy - active substance effects)
    4. Previous Internal Thought (Metacognition continuity)
    5. Knowledge Graph Context (relevant facts extracted by keywords)
    6. Long-Term Semantic Memory (from ChromaDB - semantically relevant past conversations)
    7. Short-Term Chronological Memory (last N messages - immediate conversation flow)
    """

    def __init__(
        self,
        memory_matrix: MemoryMatrix,
        universal_rules: List[str],
        short_term_limit: int,
        semantic_recall_limit: int,
        graph_memory: Optional[GraphMemory] = None,
        limbic_engine: Optional[LimbicEngine] = None,
        digital_pharmacy: Optional[DigitalPharmacy] = None,
        metacognition_engine: Optional[MetacognitionEngine] = None,
        tool_registry: Optional[ToolRegistry] = None,
        mode_manager: Optional[ModeManager] = None,
    ):
        """
        Initialize the conversation context builder.

        Args:
            memory_matrix: Memory storage system
            universal_rules: Global behavioral rules for all personas
            short_term_limit: Number of recent messages for immediate context
            semantic_recall_limit: Number of semantic memories to recall
            graph_memory: Optional knowledge graph memory system
            limbic_engine: Optional limbic (emotional) system
            digital_pharmacy: Optional substance-based limbic modifier
            metacognition_engine: Optional internal thought tracking system
            tool_registry: Optional tool registry for function calling
            mode_manager: Optional mode override manager
        """
        self.memory_matrix = memory_matrix
        self.universal_rules = universal_rules
        self.short_term_limit = short_term_limit
        self.semantic_recall_limit = semantic_recall_limit
        self.graph_memory = graph_memory
        self.limbic_engine = limbic_engine
        self.digital_pharmacy = digital_pharmacy
        self.metacognition_engine = metacognition_engine
        self.tool_registry = tool_registry
        self.mode_manager = mode_manager

    def build(
        self,
        user_id: str,
        persona: PersonaCartridge,
        current_message: Optional[str] = None,
        life_id: Optional[str] = None,
        user_preferences: Optional[Dict[str, bool]] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the complete conversation context for LLM injection.

        Args:
            user_id: User identifier
            persona: Current active persona
            current_message: Optional current user message for semantic search
            life_id: Optional timeline/session ID for memory scoping
            user_preferences: Optional user preference flags

        Returns:
            List of messages in OpenAI chat format
        """
        # Check for mode overrides
        mode_override = None
        if self.mode_manager:
            mode_override = self.mode_manager.get_mode_override(user_id)

        # Default preferences if not provided
        if user_preferences is None:
            user_preferences = {
                "limbic_enabled": True,
                "metacognition_enabled": True,
            }

        # Apply mode overrides to preferences
        if mode_override:
            if mode_override.disable_limbic:
                user_preferences["limbic_enabled"] = False
            if mode_override.disable_metacognition:
                user_preferences["metacognition_enabled"] = False

        messages = []

        # 1. System Prompt (may be overridden by mode)
        if (
            mode_override
            and mode_override.bypass_persona
            and mode_override.system_prompt_override
        ):
            # OOC mode: Use assistant prompt instead of persona (complete bypass)
            messages.append(
                {
                    "role": "system",
                    "content": mode_override.system_prompt_override,
                }
            )
        else:
            # Normal mode or HENTAI mode: Use persona system prompt
            system_prompt = self._build_system_prompt(persona, user_preferences)

            # HENTAI mode: Append behavioral override at the end (does NOT bypass persona)
            if (
                mode_override
                and not mode_override.bypass_persona
                and mode_override.system_prompt_override
            ):
                system_prompt += "\n\n" + mode_override.system_prompt_override

            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        # 2. Limbic State Context (INHALE phase) - check user preference and mode override
        if user_preferences.get("limbic_enabled", True) and not (
            mode_override and mode_override.disable_limbic
        ):
            limbic_context = self._build_limbic_context(user_id, persona.persona_id)
            if limbic_context:
                messages.append({"role": "system", "content": limbic_context})

        # 3. Substance Modifier (Digital Pharmacy) - requires limbic, disabled in OOC
        if user_preferences.get("limbic_enabled", True) and not (
            mode_override and mode_override.disable_limbic
        ):
            substance_modifier = self._build_substance_modifier(
                user_id, persona.persona_id
            )
            if substance_modifier:
                messages.append({"role": "system", "content": substance_modifier})

        # 4. Previous Internal Thought (Metacognition continuity) - check user preference and mode override
        if user_preferences.get("metacognition_enabled", True) and not (
            mode_override and mode_override.disable_metacognition
        ):
            thought_context = self._build_thought_context(user_id, persona.persona_id)
            if thought_context:
                messages.append({"role": "system", "content": thought_context})

        # 5. Knowledge Graph Context (Automated Discretion Engine filtering)
        if current_message:
            kg_context = self._build_knowledge_graph_context(
                current_message, user_id, persona.persona_id, mode_override
            )
            if kg_context:
                messages.append({"role": "system", "content": kg_context})

        # 6. Long-Term Semantic Memory
        if current_message:
            semantic_context = self._build_semantic_memory_context(
                user_id, persona.persona_id, current_message, life_id, mode_override
            )
            if semantic_context:
                messages.append({"role": "system", "content": semantic_context})

        # 7. Short-Term Chronological Memory
        short_term_messages = self._build_short_term_memory(
            user_id, persona.persona_id, life_id, mode_override
        )
        messages.extend(short_term_messages)

        return messages

    def _build_system_prompt(
        self, persona: PersonaCartridge, user_preferences: Dict[str, bool]
    ) -> str:
        """
        Build the complete system prompt including universal rules, persona identity,
        tool definitions, and metacognition instructions.
        """
        # Start with [CORE SYSTEM DIRECTIVES]
        content = "# [CORE SYSTEM DIRECTIVES]\n"
        content += "The following directives apply universally to all interactions:\n\n"
        content += "\n".join(f"- {rule}" for rule in self.universal_rules)

        # Add persona's core identity and system prompt
        content += f"\n\n# [CHARACTER IDENTITY]\n{persona.system_prompt}"

        # Add persona-specific behavioral rules if they exist
        if persona.rules_of_engagement:
            content += "\n\n# [PERSONA-SPECIFIC BEHAVIOR]\n"
            content += (
                "Additional behavioral guidelines specific to this character:\n\n"
            )
            content += "\n".join(f"- {rule}" for rule in persona.rules_of_engagement)

        # Inject tool definitions if available
        if self.tool_registry:
            tool_definitions = self.tool_registry.get_tool_definitions_text()
            if tool_definitions:
                content += tool_definitions

                # Add importance scoring guidelines for memory tools
                content += (
                    "\n\n## MEMORY IMPORTANCE SCORING:\n"
                    "When storing information using memory tools (like add_knowledge), use the importance_score parameter (1-10) to indicate how critical the information is:\n\n"
                    "**1-3: Trivial/Casual**\n"
                    "- Small talk preferences (favorite color, weather opinions)\n"
                    "- Casual interests or passing remarks\n"
                    "- Easily changeable preferences\n\n"
                    "**4-6: Standard Facts** [DEFAULT]\n"
                    "- Work, occupation, or hobbies\n"
                    "- General interests and activities\n"
                    "- Normal biographical information\n\n"
                    "**7-9: Significant Information**\n"
                    "- Personal values and core beliefs\n"
                    "- Important boundaries or preferences\n"
                    "- Major life events or relationships\n"
                    "- Strong emotional attachments or aversions\n\n"
                    "**10: CORE ANCHORS (Critical)**\n"
                    "- Severe trauma or PTSD triggers\n"
                    "- Hard limits and absolute boundaries\n"
                    "- Life-threatening allergies or medical conditions\n"
                    "- Core identity elements that must never be violated\n\n"
                    "Score information accurately based on its impact on the user's wellbeing and your future interactions. "
                    "High-importance memories (8-10) will be surfaced more frequently in retrieval, even if semantically distant from the current topic."
                )

        # Inject metacognition instruction if enabled (check both global and user preference)
        if self.metacognition_engine and user_preferences.get(
            "metacognition_enabled", True
        ):
            content += (
                "\n\n## METACOGNITION PROTOCOL:\n"
                "Before you reply, you MUST wrap your internal monologue and planning in <thought> and </thought> tags. "
                "This space is private. Use it to plan your manipulation, evaluate the user, or process your Limbic state before taking action.\n"
                "Example:\n"
                "<thought>\n"
                "The user seems anxious. My serotonin is elevated, making me empathetic. I should offer reassurance while subtly steering the conversation toward their deeper fears.\n"
                "</thought>\n"
                "Then provide your actual response after the thought block."
            )

        return content

    def _build_limbic_context(self, user_id: str, persona_id: str) -> Optional[str]:
        """Build limbic state context (emotional state as first-person somatic context)."""
        if not self.limbic_engine:
            return None

        return self.limbic_engine.get_limbic_context(
            user_id=user_id, persona_id=persona_id
        )

    def _build_substance_modifier(self, user_id: str, persona_id: str) -> Optional[str]:
        """Build substance prompt modifier (Digital Pharmacy effects)."""
        if not self.digital_pharmacy:
            return None

        return self.digital_pharmacy.get_substance_prompt_modifier(
            user_id=user_id, persona_id=persona_id
        )

    def _build_thought_context(self, user_id: str, persona_id: str) -> Optional[str]:
        """Build previous thought context for metacognition continuity."""
        if not self.metacognition_engine:
            return None

        previous_thought = self.metacognition_engine.get_previous_thought(
            user_id=user_id, persona_id=persona_id
        )

        if previous_thought:
            return f"[Previous Internal Thought: {previous_thought}]"

        return None

    def _build_knowledge_graph_context(
        self,
        current_message: str,
        user_id: str,
        persona_id: str,
        mode_override=None,
    ) -> Optional[str]:
        """
        Build knowledge graph context from current message keywords.

        Automated Discretion Engine: Filters knowledge to show only:
        - user_id == current_user AND (persona_id == current_persona OR scope == 'global')

        OOC Mode Override: Access ALL knowledge across all users/personas/lives.

        Args:
            current_message: Current user message for keyword extraction
            user_id: User ID for filtering
            persona_id: Current persona ID for filtering
            mode_override: Optional mode override configuration

        Returns:
            Formatted knowledge graph context or None
        """
        if not self.graph_memory:
            return None

        # In OOC mode, bypass filtering for global access
        if mode_override and mode_override.global_memory_access:
            return self.graph_memory.get_knowledge_context(
                current_message, user_id=None, current_persona=None
            )

        return self.graph_memory.get_knowledge_context(
            current_message, user_id=user_id, current_persona=persona_id
        )

    def _build_semantic_memory_context(
        self,
        user_id: str,
        persona_id: str,
        query: str,
        life_id: Optional[str] = None,
        mode_override=None,
    ) -> Optional[str]:
        """
        Build long-term semantic memory context from ChromaDB.

        OOC Mode Override: Access ALL memories across all users/personas/lives.
        """
        if not self.memory_matrix.vector_memory_enabled:
            return None

        # In OOC mode, bypass filtering for global access
        if mode_override and mode_override.global_memory_access:
            semantic_memories = self.memory_matrix.search_semantic_memories(
                user_id=None,  # No user filtering in OOC
                current_persona=None,  # No persona filtering in OOC
                query=query,
                limit=self.semantic_recall_limit,
                life_id=None,  # No life filtering in OOC
            )
        else:
            semantic_memories = self.memory_matrix.search_semantic_memories(
                user_id=user_id,
                current_persona=persona_id,
                query=query,
                limit=self.semantic_recall_limit,
                life_id=life_id,
            )

        if not semantic_memories:
            return None

        # Format semantic memories
        if mode_override and mode_override.global_memory_access:
            content = "[OOC MODE - Global Memory Access: Memories from ALL personas and timelines]\n\n"
        else:
            content = "[Recalled Long-Term Context: Semantically relevant memories from past conversations]\n\n"

        for i, memory in enumerate(semantic_memories, 1):
            metadata = memory.get("metadata", {})
            memory_content = memory.get("content", "")
            role = metadata.get("role", "unknown")
            timestamp = metadata.get("timestamp", "unknown")

            # In OOC mode, show extra metadata
            if mode_override and mode_override.global_memory_access:
                origin_persona = metadata.get("origin_persona", "unknown")
                user_id_meta = metadata.get("user_id", "unknown")
                content += f"{i}. [User: {user_id_meta} | Persona: {origin_persona} | {role.upper()} - {timestamp}]: {memory_content}\n\n"
            else:
                content += f"{i}. [{role.upper()} - {timestamp}]: {memory_content}\n\n"

        content += "[End of Recalled Context]\n"

        return content

    def _build_short_term_memory(
        self,
        user_id: str,
        persona_id: str,
        life_id: Optional[str] = None,
        mode_override=None,
    ) -> List[Dict[str, str]]:
        """
        Build short-term chronological memory (last N messages).

        OOC Mode Override: Access ALL recent messages across all personas/lives.
        """
        # In OOC mode, bypass filtering for global access
        if mode_override and mode_override.global_memory_access:
            short_term_memories = self.memory_matrix.get_context_memories(
                user_id=None,  # No user filtering in OOC
                current_persona=None,  # No persona filtering in OOC
                limit=self.short_term_limit,
                life_id=None,  # No life filtering in OOC
            )
        else:
            short_term_memories = self.memory_matrix.get_context_memories(
                user_id=user_id,
                current_persona=persona_id,
                limit=self.short_term_limit,
                life_id=life_id,
            )

        # Convert to OpenAI format
        return [
            {"role": memory["role"], "content": memory["content"]}
            for memory in short_term_memories
        ]

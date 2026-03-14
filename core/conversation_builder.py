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
        # Default preferences if not provided
        if user_preferences is None:
            user_preferences = {
                "limbic_enabled": True,
                "metacognition_enabled": True,
            }

        messages = []

        # 1. System Prompt
        messages.append(
            {
                "role": "system",
                "content": self._build_system_prompt(persona, user_preferences),
            }
        )

        # 2. Limbic State Context (INHALE phase) - check user preference
        if user_preferences.get("limbic_enabled", True):
            limbic_context = self._build_limbic_context(user_id, persona.persona_id)
            if limbic_context:
                messages.append({"role": "system", "content": limbic_context})

        # 3. Substance Modifier (Digital Pharmacy) - requires limbic
        if user_preferences.get("limbic_enabled", True):
            substance_modifier = self._build_substance_modifier(
                user_id, persona.persona_id
            )
            if substance_modifier:
                messages.append({"role": "system", "content": substance_modifier})

        # 4. Previous Internal Thought (Metacognition continuity) - check user preference
        if user_preferences.get("metacognition_enabled", True):
            thought_context = self._build_thought_context(user_id, persona.persona_id)
            if thought_context:
                messages.append({"role": "system", "content": thought_context})

        # 5. Knowledge Graph Context (Automated Discretion Engine filtering)
        if current_message:
            kg_context = self._build_knowledge_graph_context(
                current_message, user_id, persona.persona_id
            )
            if kg_context:
                messages.append({"role": "system", "content": kg_context})

        # 6. Long-Term Semantic Memory
        if current_message:
            semantic_context = self._build_semantic_memory_context(
                user_id, persona.persona_id, current_message, life_id
            )
            if semantic_context:
                messages.append({"role": "system", "content": semantic_context})

        # 7. Short-Term Chronological Memory
        short_term_messages = self._build_short_term_memory(
            user_id, persona.persona_id, life_id
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
    ) -> Optional[str]:
        """
        Build knowledge graph context from current message keywords.

        Automated Discretion Engine: Filters knowledge to show only:
        - user_id == current_user AND (persona_id == current_persona OR scope == 'global')

        Args:
            current_message: Current user message for keyword extraction
            user_id: User ID for filtering
            persona_id: Current persona ID for filtering

        Returns:
            Formatted knowledge graph context or None
        """
        if not self.graph_memory:
            return None

        return self.graph_memory.get_knowledge_context(
            current_message, user_id=user_id, current_persona=persona_id
        )

    def _build_semantic_memory_context(
        self,
        user_id: str,
        persona_id: str,
        query: str,
        life_id: Optional[str] = None,
    ) -> Optional[str]:
        """Build long-term semantic memory context from ChromaDB."""
        if not self.memory_matrix.vector_memory_enabled:
            return None

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
        content = "[Recalled Long-Term Context: Semantically relevant memories from past conversations]\n\n"
        for i, memory in enumerate(semantic_memories, 1):
            metadata = memory.get("metadata", {})
            memory_content = memory.get("content", "")
            role = metadata.get("role", "unknown")
            timestamp = metadata.get("timestamp", "unknown")

            content += f"{i}. [{role.upper()} - {timestamp}]: {memory_content}\n\n"

        content += "[End of Recalled Context]\n"

        return content

    def _build_short_term_memory(
        self, user_id: str, persona_id: str, life_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build short-term chronological memory (last N messages)."""
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

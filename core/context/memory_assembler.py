"""
Memory Assembler - Retrieves and formats memories from different storage systems.

This module handles:
- Short-term chronological memory (SQLite - last N messages)
- Long-term semantic memory (ChromaDB - vector search)
- Knowledge graph context (Neo4j/graph - entity/relationship facts)

Part of the Hybrid Memory Architecture split from conversation_builder.py.
Created during RDSSC Phase 1.
"""

from typing import List, Dict, Optional

from database.memory_matrix import MemoryMatrix
from database.graph_memory import GraphMemory


class MemoryAssembler:
    """
    Assembles memory context from multiple storage systems.

    MEMORY LAYERS:
    1. Knowledge Graph Context (relevant facts extracted by keywords)
    2. Long-Term Semantic Memory (ChromaDB - semantically relevant past conversations)
    3. Short-Term Chronological Memory (last N messages - immediate conversation flow)
    """

    def __init__(
        self,
        memory_matrix: MemoryMatrix,
        short_term_limit: int,
        semantic_recall_limit: int,
        graph_memory: Optional[GraphMemory] = None,
    ):
        """
        Initialize the memory assembler.

        Args:
            memory_matrix: Memory storage system (SQLite + ChromaDB)
            short_term_limit: Number of recent messages for immediate context
            semantic_recall_limit: Number of semantic memories to recall
            graph_memory: Optional knowledge graph memory system
        """
        self.memory_matrix = memory_matrix
        self.short_term_limit = short_term_limit
        self.semantic_recall_limit = semantic_recall_limit
        self.graph_memory = graph_memory

    def build_knowledge_graph_context(
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

    def build_semantic_memory_context(
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

        Args:
            user_id: User ID for filtering
            persona_id: Current persona ID for filtering
            query: Search query for semantic retrieval
            life_id: Optional timeline/session ID for memory scoping
            mode_override: Optional mode override configuration

        Returns:
            Formatted semantic memory context or None
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

    def build_short_term_memory(
        self,
        user_id: str,
        persona_id: str,
        life_id: Optional[str] = None,
        mode_override=None,
    ) -> List[Dict[str, str]]:
        """
        Build short-term chronological memory (last N messages).

        OOC Mode Override: Access ALL recent messages across all personas/lives.

        Args:
            user_id: User ID for filtering
            persona_id: Current persona ID for filtering
            life_id: Optional timeline/session ID for memory scoping
            mode_override: Optional mode override configuration

        Returns:
            List of messages in OpenAI chat format
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

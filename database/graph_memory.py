"""
Knowledge Graph Memory - Facade for Project Myriad's knowledge graph subsystems.

This module provides a unified interface to:
1. Entity and relationship storage (graph database)
2. Keyword extraction and search
3. Context formatting for LLM injection

Part of RDSSC Phase 6: Refactored to delegate to focused modules.
"""

from typing import List, Dict, Any, Optional
from database.graph_repository import GraphRepository
from database.graph_search import GraphSearch


class GraphMemory:
    """
    Facade for knowledge graph operations.

    Delegates to specialized modules:
    - GraphRepository: Entity and relationship CRUD
    - GraphSearch: Keyword extraction and search operations
    """

    def __init__(self, db_path: str = "data/knowledge_graph.db"):
        """
        Initialize the knowledge graph subsystems.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

        # Initialize subsystem managers
        self.repository = GraphRepository(db_path)
        self.search = GraphSearch(db_path, self.repository)

    # ========================
    # ENTITY & RELATIONSHIP CRUD
    # (Delegated to GraphRepository)
    # ========================

    def add_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        importance_score: int = 5,
    ) -> int:
        """
        Add or update an entity in the knowledge graph.

        Args:
            name: Entity name (e.g., "Bob", "Python", "Gentle Possession")
            entity_type: Category (e.g., "User", "Language", "Concept")
            description: Optional description of the entity
            importance_score: Importance rating 1-10 (default: 5)

        Returns:
            Entity ID (existing or newly created)
        """
        return self.repository.add_entity(
            name, entity_type, description, importance_score
        )

    def add_relationship(
        self,
        entity1: str,
        entity1_type: str,
        relation: str,
        entity2: str,
        entity2_type: str,
        importance_score: int = 5,
    ) -> bool:
        """
        Add a relationship between two entities.
        Creates entities if they don't exist.

        Args:
            entity1: Source entity name
            entity1_type: Source entity type
            relation: Relationship type (e.g., "LIKES", "KNOWS", "CREATED")
            entity2: Target entity name
            entity2_type: Target entity type
            importance_score: Importance rating 1-10 (default: 5)

        Returns:
            True if relationship was added/updated, False on error

        Example:
            add_relationship("Bob", "User", "LIKES", "Gentle Possession", "Concept", importance_score=7)
        """
        return self.repository.add_relationship(
            entity1, entity1_type, relation, entity2, entity2_type, importance_score
        )

    def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find an entity by name (case-insensitive).

        Args:
            name: Entity name to search for

        Returns:
            Entity dictionary or None if not found
        """
        return self.repository.get_entity_by_name(name)

    def get_relationships_for_entity(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get all relationships connected to an entity (incoming and outgoing).

        Args:
            entity_name: Name of the entity

        Returns:
            List of relationship dictionaries with entity details
        """
        return self.repository.get_relationships_for_entity(entity_name)

    def get_all_relationships(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all relationships in the knowledge graph.

        Args:
            limit: Maximum number of relationships to return

        Returns:
            List of all relationships
        """
        return self.repository.get_all_relationships(limit)

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the knowledge graph.

        Returns:
            Dictionary with entity and relationship counts
        """
        return self.repository.get_stats()

    def clear_all(self):
        """Clear all data from the knowledge graph (for testing)."""
        self.repository.clear_all()

    # ========================
    # SEARCH & CONTEXT BUILDING
    # (Delegated to GraphSearch)
    # ========================

    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Extract potential keywords from text for entity matching.

        Args:
            text: Input text to extract keywords from
            min_length: Minimum keyword length (default: 3)

        Returns:
            List of extracted keywords
        """
        return self.search.extract_keywords(text, min_length)

    def search_entities_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for entities matching any of the provided keywords.

        Args:
            keywords: List of search terms

        Returns:
            List of matching entities with their relationships
        """
        return self.search.search_entities_by_keywords(keywords)

    def get_knowledge_context(self, user_message: str) -> str:
        """
        Extract keywords from user message and retrieve relevant knowledge graph context.

        This is the main retrieval function called by AgentCore.

        Args:
            user_message: The user's input message

        Returns:
            Formatted knowledge graph context for injection into system prompt
        """
        return self.search.get_knowledge_context(user_message)

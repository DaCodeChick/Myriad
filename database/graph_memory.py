"""
Knowledge Graph Memory - Entity-Relationship Storage for Project Myriad.

This module stores factual knowledge as a graph of entities and relationships.
When the LLM learns important facts, it can call tools to permanently store them.

Example:
    - Entity: "Bob" (type: "User")
    - Relationship: "LIKES"
    - Entity: "Gentle Possession" (type: "Concept")

The graph is queried using keyword extraction to inject relevant context
into the LLM's system prompt.
"""

import sqlite3
from typing import List, Dict, Any, Optional, Tuple
import re


class GraphMemory:
    """
    Manages the Knowledge Graph using SQLite.

    Tables:
        - entities: Stores nodes (people, concepts, objects, etc.)
        - relationships: Stores edges between entities
    """

    def __init__(self, db_path: str = "data/knowledge_graph.db"):
        """
        Initialize the Knowledge Graph database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create the entities and relationships tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Entities table: Stores knowledge graph nodes
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE,
                type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, type)
            )
        """
        )

        # Index for fast entity lookups by name
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entity_name 
            ON entities(name COLLATE NOCASE)
        """
        )

        # Relationships table: Stores knowledge graph edges
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, relation_type)
            )
        """
        )

        # Index for fast relationship lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relationship_source 
            ON relationships(source_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relationship_target 
            ON relationships(target_id)
        """
        )

        conn.commit()
        conn.close()

    def add_entity(
        self, name: str, entity_type: str, description: Optional[str] = None
    ) -> int:
        """
        Add or update an entity in the knowledge graph.

        Args:
            name: Entity name (e.g., "Bob", "Python", "Gentle Possession")
            entity_type: Category (e.g., "User", "Language", "Concept")
            description: Optional description of the entity

        Returns:
            Entity ID (existing or newly created)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Try to insert new entity
            cursor.execute(
                """
                INSERT INTO entities (name, type, description)
                VALUES (?, ?, ?)
            """,
                (name.strip(), entity_type.strip(), description),
            )
            entity_id = cursor.lastrowid
            conn.commit()

        except sqlite3.IntegrityError:
            # Entity already exists, get its ID and update description if provided
            cursor.execute(
                """
                SELECT id FROM entities 
                WHERE name = ? COLLATE NOCASE AND type = ?
            """,
                (name.strip(), entity_type.strip()),
            )
            entity_id = cursor.fetchone()[0]

            # Update description if provided
            if description:
                cursor.execute(
                    """
                    UPDATE entities 
                    SET description = ? 
                    WHERE id = ?
                """,
                    (description, entity_id),
                )
                conn.commit()

        conn.close()
        return entity_id

    def add_relationship(
        self,
        entity1: str,
        entity1_type: str,
        relation: str,
        entity2: str,
        entity2_type: str,
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

        Returns:
            True if relationship was added/updated, False on error

        Example:
            add_relationship("Bob", "User", "LIKES", "Gentle Possession", "Concept")
        """
        try:
            # Ensure both entities exist
            source_id = self.add_entity(entity1, entity1_type)
            target_id = self.add_entity(entity2, entity2_type)

            # Add the relationship
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type)
                VALUES (?, ?, ?)
            """,
                (source_id, target_id, relation.strip().upper()),
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error adding relationship: {e}")
            return False

    def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find an entity by name (case-insensitive).

        Args:
            name: Entity name to search for

        Returns:
            Entity dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, type, description, created_at
            FROM entities
            WHERE name = ? COLLATE NOCASE
            LIMIT 1
        """,
            (name.strip(),),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "description": row[3],
                "created_at": row[4],
            }
        return None

    def get_relationships_for_entity(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get all relationships connected to an entity (incoming and outgoing).

        Args:
            entity_name: Name of the entity

        Returns:
            List of relationship dictionaries with entity details

        Example result:
            [
                {
                    "source": "Bob",
                    "source_type": "User",
                    "relation": "LIKES",
                    "target": "Gentle Possession",
                    "target_type": "Concept"
                }
            ]
        """
        entity = self.get_entity_by_name(entity_name)
        if not entity:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all relationships where this entity is source or target
        cursor.execute(
            """
            SELECT 
                e1.name as source_name,
                e1.type as source_type,
                r.relation_type,
                e2.name as target_name,
                e2.type as target_type
            FROM relationships r
            JOIN entities e1 ON r.source_id = e1.id
            JOIN entities e2 ON r.target_id = e2.id
            WHERE r.source_id = ? OR r.target_id = ?
            ORDER BY r.created_at DESC
        """,
            (entity["id"], entity["id"]),
        )

        rows = cursor.fetchall()
        conn.close()

        relationships = []
        for row in rows:
            relationships.append(
                {
                    "source": row[0],
                    "source_type": row[1],
                    "relation": row[2],
                    "target": row[3],
                    "target_type": row[4],
                }
            )

        return relationships

    def search_entities_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for entities matching any of the provided keywords.

        Args:
            keywords: List of search terms

        Returns:
            List of matching entities with their relationships
        """
        if not keywords:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query to search for any keyword in entity names
        placeholders = " OR ".join(["name LIKE ? COLLATE NOCASE"] * len(keywords))
        query_params = [f"%{kw}%" for kw in keywords]

        cursor.execute(
            f"""
            SELECT DISTINCT name
            FROM entities
            WHERE {placeholders}
        """,
            query_params,
        )

        rows = cursor.fetchall()
        conn.close()

        # Get relationships for each matching entity
        results = []
        for row in rows:
            entity_name = row[0]
            relationships = self.get_relationships_for_entity(entity_name)
            if relationships:
                results.append({"entity": entity_name, "relationships": relationships})

        return results

    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Extract potential keywords from text for entity matching.

        Simple implementation: Split on whitespace, remove punctuation,
        filter by length, and capitalize for proper noun matching.

        Args:
            text: Input text to extract keywords from
            min_length: Minimum keyword length (default: 3)

        Returns:
            List of extracted keywords
        """
        # Remove common punctuation but keep alphanumeric and spaces
        cleaned = re.sub(r"[^\w\s]", " ", text)

        # Split into words
        words = cleaned.split()

        # Filter by length and remove common stop words
        stop_words = {
            "the",
            "is",
            "are",
            "was",
            "were",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "an",
            "a",
            "this",
            "that",
            "these",
            "those",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
        }

        keywords = [
            word
            for word in words
            if len(word) >= min_length and word.lower() not in stop_words
        ]

        # Return unique keywords, preserving case for proper noun matching
        return list(set(keywords))

    def get_knowledge_context(self, user_message: str) -> str:
        """
        Extract keywords from user message and retrieve relevant knowledge graph context.

        This is the main retrieval function called by AgentCore.

        Args:
            user_message: The user's input message

        Returns:
            Formatted knowledge graph context for injection into system prompt
        """
        # Extract keywords from message
        keywords = self.extract_keywords(user_message)

        if not keywords:
            return ""

        # Search for matching entities
        results = self.search_entities_by_keywords(keywords)

        if not results:
            return ""

        # Format as context for LLM
        context = "\n\n## KNOWLEDGE GRAPH CONTEXT:\n\n"
        context += "Relevant facts from your knowledge graph:\n\n"

        for result in results:
            entity = result["entity"]
            relationships = result["relationships"]

            context += f"**{entity}:**\n"
            for rel in relationships:
                context += f"  • {rel['source']} ({rel['source_type']}) {rel['relation']} {rel['target']} ({rel['target_type']})\n"
            context += "\n"

        context += "Use this knowledge to inform your response, but only mention it if relevant to the conversation.\n"

        return context

    def get_all_relationships(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all relationships in the knowledge graph.

        Args:
            limit: Maximum number of relationships to return

        Returns:
            List of all relationships
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                e1.name as source_name,
                e1.type as source_type,
                r.relation_type,
                e2.name as target_name,
                e2.type as target_type
            FROM relationships r
            JOIN entities e1 ON r.source_id = e1.id
            JOIN entities e2 ON r.target_id = e2.id
            ORDER BY r.created_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        relationships = []
        for row in rows:
            relationships.append(
                {
                    "source": row[0],
                    "source_type": row[1],
                    "relation": row[2],
                    "target": row[3],
                    "target_type": row[4],
                }
            )

        return relationships

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the knowledge graph.

        Returns:
            Dictionary with entity and relationship counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM relationships")
        relationship_count = cursor.fetchone()[0]

        conn.close()

        return {
            "total_entities": entity_count,
            "total_relationships": relationship_count,
        }

    def clear_all(self):
        """Clear all data from the knowledge graph (for testing)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM relationships")
        cursor.execute("DELETE FROM entities")

        conn.commit()
        conn.close()

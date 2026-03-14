"""
Knowledge Graph Repository - Entity and Relationship CRUD for Project Myriad.

This module handles low-level database operations for the knowledge graph:
- Entity creation and retrieval
- Relationship creation and retrieval
- Database schema management

Part of RDSSC Phase 6: Split graph_memory.py into focused modules.
"""

import sqlite3
from typing import List, Dict, Any, Optional


class GraphRepository:
    """Handles entity and relationship CRUD operations for the knowledge graph."""

    def __init__(self, db_path: str = "data/knowledge_graph.db"):
        """
        Initialize the knowledge graph repository.

        Args:
            db_path: Path to SQLite database file
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
                importance_score INTEGER DEFAULT 5,
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
                importance_score INTEGER DEFAULT 5,
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
            importance_score: Importance rating 1-10 (default=5)
                1-3: Trivial/casual information
                4-6: Standard facts
                7-9: Significant information
                10: Core anchors (trauma, hard limits)

        Returns:
            Entity ID (existing or newly created)
        """
        # Clamp importance_score to valid range
        importance_score = max(1, min(10, importance_score))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        entity_id: int = 0  # Initialize to satisfy type checker

        try:
            # Try to insert new entity
            cursor.execute(
                """
                INSERT INTO entities (name, type, description, importance_score)
                VALUES (?, ?, ?, ?)
            """,
                (name.strip(), entity_type.strip(), description, importance_score),
            )
            entity_id = cursor.lastrowid or 0
            conn.commit()

        except sqlite3.IntegrityError:
            # Entity already exists, get its ID and update description/importance if provided
            cursor.execute(
                """
                SELECT id FROM entities 
                WHERE name = ? COLLATE NOCASE AND type = ?
            """,
                (name.strip(), entity_type.strip()),
            )
            result = cursor.fetchone()
            if result is None:
                conn.close()
                raise ValueError(f"Entity lookup failed for: {name} ({entity_type})")
            entity_id = int(result[0])

            # Update description and importance if provided
            if description or importance_score != 5:
                cursor.execute(
                    """
                    UPDATE entities 
                    SET description = COALESCE(?, description),
                        importance_score = ?
                    WHERE id = ?
                """,
                    (description, importance_score, entity_id),
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
            importance_score: Importance rating 1-10 (default=5)
                1-3: Trivial/casual information
                4-6: Standard facts
                7-9: Significant information
                10: Core anchors (trauma, hard limits)

        Returns:
            True if relationship was added/updated, False on error

        Example:
            add_relationship("Bob", "User", "LIKES", "Gentle Possession", "Concept", importance_score=7)
        """
        try:
            # Clamp importance_score to valid range
            importance_score = max(1, min(10, importance_score))

            # Ensure both entities exist
            source_id = self.add_entity(entity1, entity1_type)
            target_id = self.add_entity(entity2, entity2_type)

            # Add the relationship
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO relationships (source_id, target_id, relation_type, importance_score)
                VALUES (?, ?, ?, ?)
            """,
                (source_id, target_id, relation.strip().upper(), importance_score),
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
            SELECT id, name, type, description, importance_score, created_at
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
                "importance_score": row[4],
                "created_at": row[5],
            }
        return None

    def get_relationships_for_entity(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get all relationships connected to an entity (incoming and outgoing).
        Sorted by importance_score (highest first).

        Args:
            entity_name: Name of the entity

        Returns:
            List of relationship dictionaries with entity details and importance scores

        Example result:
            [
                {
                    "source": "Bob",
                    "source_type": "User",
                    "relation": "LIKES",
                    "target": "Gentle Possession",
                    "target_type": "Concept",
                    "importance_score": 7
                }
            ]
        """
        entity = self.get_entity_by_name(entity_name)
        if not entity:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all relationships where this entity is source or target
        # Sort by importance_score descending (highest importance first)
        cursor.execute(
            """
            SELECT 
                e1.name as source_name,
                e1.type as source_type,
                r.relation_type,
                e2.name as target_name,
                e2.type as target_type,
                r.importance_score
            FROM relationships r
            JOIN entities e1 ON r.source_id = e1.id
            JOIN entities e2 ON r.target_id = e2.id
            WHERE r.source_id = ? OR r.target_id = ?
            ORDER BY r.importance_score DESC, r.created_at DESC
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
                    "importance_score": row[5]
                    if len(row) > 5
                    else 5,  # Default to 5 if missing
                }
            )

        return relationships

    def get_all_relationships(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all relationships in the knowledge graph.
        Sorted by importance_score (highest first).

        Args:
            limit: Maximum number of relationships to return

        Returns:
            List of all relationships with importance scores
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
                e2.type as target_type,
                r.importance_score
            FROM relationships r
            JOIN entities e1 ON r.source_id = e1.id
            JOIN entities e2 ON r.target_id = e2.id
            ORDER BY r.importance_score DESC, r.created_at DESC
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
                    "importance_score": row[5]
                    if len(row) > 5
                    else 5,  # Default to 5 if missing
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

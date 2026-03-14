"""
Knowledge Graph Repository - Entity and Relationship CRUD for Project Myriad.

This module handles low-level database operations for the knowledge graph:
- Entity creation and retrieval
- Relationship creation and retrieval
- Database schema management

Part of RDSSC Phase 6: Split graph_memory.py into focused modules.
Updated for Automated Discretion Engine: user_id, persona_id, and scope columns.
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
        # Updated: Added user_id, persona_id, scope for Automated Discretion Engine
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE,
                type TEXT NOT NULL,
                description TEXT,
                importance_score INTEGER DEFAULT 5,
                user_id TEXT NOT NULL DEFAULT '',
                persona_id TEXT NOT NULL DEFAULT '',
                scope TEXT NOT NULL DEFAULT 'isolated',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, type, user_id, persona_id)
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

        # Index for user/persona filtering (Automated Discretion Engine)
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entity_user_persona
            ON entities(user_id, persona_id, scope)
        """
        )

        # Relationships table: Stores knowledge graph edges
        # Updated: Added user_id, persona_id, scope for Automated Discretion Engine
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                importance_score INTEGER DEFAULT 5,
                user_id TEXT NOT NULL DEFAULT '',
                persona_id TEXT NOT NULL DEFAULT '',
                scope TEXT NOT NULL DEFAULT 'isolated',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, relation_type, user_id, persona_id)
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

        # Index for user/persona filtering (Automated Discretion Engine)
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relationship_user_persona
            ON relationships(user_id, persona_id, scope)
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
        user_id: str = "",
        persona_id: str = "",
        scope: str = "isolated",
    ) -> int:
        """
        Add or update an entity in the knowledge graph.

        Args:
            name: Entity name (e.g., "Bob", "Python", "Gentle Possession")
            entity_type: Category (e.g., "User", "Language", "Concept")
            description: Optional description of the entity
            importance_score: Importance rating 1-10 (default=5)
            user_id: User ID for scoping (Automated Discretion Engine)
            persona_id: Persona ID for scoping (Automated Discretion Engine)
            scope: Memory scope - 'isolated' or 'global' (Automated Discretion Engine)

        Returns:
            Entity ID (existing or newly created)
        """
        # Clamp importance_score to valid range
        importance_score = max(1, min(10, importance_score))

        # Validate scope
        if scope not in ("isolated", "global"):
            scope = "isolated"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        entity_id: int = 0  # Initialize to satisfy type checker

        try:
            # Try to insert new entity
            cursor.execute(
                """
                INSERT INTO entities (name, type, description, importance_score, user_id, persona_id, scope)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name.strip(),
                    entity_type.strip(),
                    description,
                    importance_score,
                    user_id,
                    persona_id,
                    scope,
                ),
            )
            entity_id = cursor.lastrowid or 0
            conn.commit()

        except sqlite3.IntegrityError:
            # Entity already exists, get its ID and update description/importance if provided
            cursor.execute(
                """
                SELECT id FROM entities 
                WHERE name = ? COLLATE NOCASE AND type = ? AND user_id = ? AND persona_id = ?
            """,
                (name.strip(), entity_type.strip(), user_id, persona_id),
            )
            result = cursor.fetchone()
            if result is None:
                conn.close()
                raise ValueError(f"Entity lookup failed for: {name} ({entity_type})")
            entity_id = int(result[0])

            # Update description, importance, and scope if provided
            if description or importance_score != 5:
                cursor.execute(
                    """
                    UPDATE entities 
                    SET description = COALESCE(?, description),
                        importance_score = ?,
                        scope = ?
                    WHERE id = ?
                """,
                    (description, importance_score, scope, entity_id),
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
        user_id: str = "",
        persona_id: str = "",
        scope: str = "isolated",
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
            user_id: User ID for scoping (Automated Discretion Engine)
            persona_id: Persona ID for scoping (Automated Discretion Engine)
            scope: Memory scope - 'isolated' or 'global' (Automated Discretion Engine)

        Returns:
            True if relationship was added/updated, False on error

        Example:
            add_relationship("Bob", "User", "LIKES", "Gentle Possession", "Concept",
                            importance_score=7, user_id="123", persona_id="mira", scope="isolated")
        """
        try:
            # Clamp importance_score to valid range
            importance_score = max(1, min(10, importance_score))

            # Validate scope
            if scope not in ("isolated", "global"):
                scope = "isolated"

            # Ensure both entities exist (with same user/persona/scope context)
            source_id = self.add_entity(
                entity1,
                entity1_type,
                user_id=user_id,
                persona_id=persona_id,
                scope=scope,
            )
            target_id = self.add_entity(
                entity2,
                entity2_type,
                user_id=user_id,
                persona_id=persona_id,
                scope=scope,
            )

            # Add the relationship
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO relationships 
                (source_id, target_id, relation_type, importance_score, user_id, persona_id, scope)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    source_id,
                    target_id,
                    relation.strip().upper(),
                    importance_score,
                    user_id,
                    persona_id,
                    scope,
                ),
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error adding relationship: {e}")
            return False

    def get_entity_by_name(
        self,
        name: str,
        user_id: Optional[str] = None,
        persona_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find an entity by name (case-insensitive).
        Optionally filter by user_id and persona_id.

        Args:
            name: Entity name to search for
            user_id: Optional user ID filter
            persona_id: Optional persona ID filter

        Returns:
            Entity dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if user_id is not None and persona_id is not None:
            cursor.execute(
                """
                SELECT id, name, type, description, importance_score, user_id, persona_id, scope, created_at
                FROM entities
                WHERE name = ? COLLATE NOCASE AND user_id = ? AND persona_id = ?
                LIMIT 1
            """,
                (name.strip(), user_id, persona_id),
            )
        else:
            cursor.execute(
                """
                SELECT id, name, type, description, importance_score, user_id, persona_id, scope, created_at
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
                "user_id": row[5],
                "persona_id": row[6],
                "scope": row[7],
                "created_at": row[8],
            }
        return None

    def get_relationships_for_entity(
        self,
        entity_name: str,
        user_id: Optional[str] = None,
        current_persona: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all relationships connected to an entity (incoming and outgoing).
        Sorted by importance_score (highest first).

        Automated Discretion Engine: If user_id and current_persona provided,
        returns relationships where:
        - user_id matches AND (persona_id matches OR scope == 'global')

        Args:
            entity_name: Name of the entity
            user_id: User ID for filtering (Automated Discretion Engine)
            current_persona: Current persona ID for filtering (Automated Discretion Engine)

        Returns:
            List of relationship dictionaries with entity details and importance scores
        """
        entity = self.get_entity_by_name(entity_name)
        if not entity:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query based on whether we're filtering by user/persona
        if user_id is not None and current_persona is not None:
            # Automated Discretion Engine: The Funnel
            # user_id == current_user AND (persona_id == current_persona OR scope == 'global')
            cursor.execute(
                """
                SELECT 
                    e1.name as source_name,
                    e1.type as source_type,
                    r.relation_type,
                    e2.name as target_name,
                    e2.type as target_type,
                    r.importance_score,
                    r.scope
                FROM relationships r
                JOIN entities e1 ON r.source_id = e1.id
                JOIN entities e2 ON r.target_id = e2.id
                WHERE (r.source_id = ? OR r.target_id = ?)
                  AND r.user_id = ?
                  AND (r.persona_id = ? OR r.scope = 'global')
                ORDER BY r.importance_score DESC, r.created_at DESC
            """,
                (entity["id"], entity["id"], user_id, current_persona),
            )
        else:
            # Legacy mode: return all relationships for entity
            cursor.execute(
                """
                SELECT 
                    e1.name as source_name,
                    e1.type as source_type,
                    r.relation_type,
                    e2.name as target_name,
                    e2.type as target_type,
                    r.importance_score,
                    r.scope
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
                    "importance_score": row[5] if row[5] is not None else 5,
                    "scope": row[6] if len(row) > 6 else "isolated",
                }
            )

        return relationships

    def get_all_relationships(
        self,
        limit: int = 100,
        user_id: Optional[str] = None,
        current_persona: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all relationships in the knowledge graph.
        Sorted by importance_score (highest first).

        Automated Discretion Engine: If user_id and current_persona provided,
        filters by user and (persona OR global scope).

        Args:
            limit: Maximum number of relationships to return
            user_id: User ID for filtering (Automated Discretion Engine)
            current_persona: Current persona ID for filtering (Automated Discretion Engine)

        Returns:
            List of all relationships with importance scores
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if user_id is not None and current_persona is not None:
            # Automated Discretion Engine: The Funnel
            cursor.execute(
                """
                SELECT 
                    e1.name as source_name,
                    e1.type as source_type,
                    r.relation_type,
                    e2.name as target_name,
                    e2.type as target_type,
                    r.importance_score,
                    r.scope
                FROM relationships r
                JOIN entities e1 ON r.source_id = e1.id
                JOIN entities e2 ON r.target_id = e2.id
                WHERE r.user_id = ?
                  AND (r.persona_id = ? OR r.scope = 'global')
                ORDER BY r.importance_score DESC, r.created_at DESC
                LIMIT ?
            """,
                (user_id, current_persona, limit),
            )
        else:
            cursor.execute(
                """
                SELECT 
                    e1.name as source_name,
                    e1.type as source_type,
                    r.relation_type,
                    e2.name as target_name,
                    e2.type as target_type,
                    r.importance_score,
                    r.scope
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
                    "importance_score": row[5] if row[5] is not None else 5,
                    "scope": row[6] if len(row) > 6 else "isolated",
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

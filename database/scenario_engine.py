"""
Scenario Engine (World Tree) for Project Myriad.

This module manages hierarchical environmental contexts that allow the AI to understand
nested locations and world states (e.g., a room within a building within a city within an era).

The system uses a self-referencing tree structure where scenarios can be nested infinitely.
"""

import sqlite3
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Scenario:
    """Represents a scenario/location in the world tree."""

    id: int
    name: str
    description: str
    parent_id: Optional[int] = None


class ScenarioEngine:
    """Manages hierarchical scenario contexts (World Tree)."""

    def __init__(self, db_path: str):
        """
        Initialize scenario engine.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Ensure scenarios table and active_scenario_id column exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create scenarios table with self-referencing foreign key
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES scenarios(id) ON DELETE SET NULL
            )
        """
        )

        # Create index on parent_id for faster tree traversal
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scenarios_parent_id 
            ON scenarios(parent_id)
        """
        )

        # Add active_scenario_id to user_state table if it doesn't exist
        # First check if the column exists
        cursor.execute("PRAGMA table_info(user_state)")
        columns = [row[1] for row in cursor.fetchall()]

        if "active_scenario_id" not in columns:
            cursor.execute(
                """
                ALTER TABLE user_state 
                ADD COLUMN active_scenario_id INTEGER
            """
            )

        conn.commit()
        conn.close()

    def create_scenario(
        self, name: str, description: str, parent_id: Optional[int] = None
    ) -> Scenario:
        """
        Create a new scenario.

        Args:
            name: Unique name for the scenario
            description: Detailed description of this scenario/location
            parent_id: Optional ID of parent scenario to nest this within

        Returns:
            The created Scenario object

        Raises:
            sqlite3.IntegrityError: If scenario name already exists
            ValueError: If parent_id doesn't exist
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Verify parent exists if parent_id is provided
        if parent_id is not None:
            cursor.execute("SELECT id FROM scenarios WHERE id = ?", (parent_id,))
            if cursor.fetchone() is None:
                conn.close()
                raise ValueError(f"Parent scenario with ID {parent_id} does not exist")

        try:
            cursor.execute(
                """
                INSERT INTO scenarios (name, description, parent_id)
                VALUES (?, ?, ?)
            """,
                (name, description, parent_id),
            )
            scenario_id = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.close()
            raise sqlite3.IntegrityError(f"Scenario '{name}' already exists") from e

        conn.close()

        return Scenario(
            id=scenario_id, name=name, description=description, parent_id=parent_id
        )

    def get_scenario(self, name: str) -> Optional[Scenario]:
        """
        Get a scenario by name.

        Args:
            name: Name of the scenario

        Returns:
            Scenario object or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, description, parent_id FROM scenarios WHERE name = ?",
            (name,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return Scenario(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                parent_id=row["parent_id"],
            )
        return None

    def get_scenario_by_id(self, scenario_id: int) -> Optional[Scenario]:
        """
        Get a scenario by ID.

        Args:
            scenario_id: ID of the scenario

        Returns:
            Scenario object or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, description, parent_id FROM scenarios WHERE id = ?",
            (scenario_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return Scenario(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                parent_id=row["parent_id"],
            )
        return None

    def get_scenario_hierarchy(self, scenario_id: int) -> List[Scenario]:
        """
        Get the full hierarchy from root to the specified scenario using recursive CTE.

        This returns scenarios from MACRO (highest parent) to MICRO (the active scenario).

        Args:
            scenario_id: ID of the scenario to get hierarchy for

        Returns:
            List of Scenario objects from root to current, ordered macro->micro
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Recursive CTE to traverse from child up to root, then reverse the order
        cursor.execute(
            """
            WITH RECURSIVE scenario_path AS (
                -- Base case: start with the active scenario
                SELECT id, name, description, parent_id, 0 as depth
                FROM scenarios
                WHERE id = ?
                
                UNION ALL
                
                -- Recursive case: get parent scenarios
                SELECT s.id, s.name, s.description, s.parent_id, sp.depth + 1
                FROM scenarios s
                INNER JOIN scenario_path sp ON s.id = sp.parent_id
            )
            SELECT id, name, description, parent_id, depth
            FROM scenario_path
            ORDER BY depth DESC  -- Root first (highest depth), active last (depth 0)
        """,
            (scenario_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        scenarios = []
        for row in rows:
            scenarios.append(
                Scenario(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    parent_id=row["parent_id"],
                )
            )

        return scenarios

    def set_parent(self, child_name: str, parent_name: str) -> None:
        """
        Set the parent of a scenario, creating a hierarchical relationship.

        Args:
            child_name: Name of the child scenario
            parent_name: Name of the parent scenario

        Raises:
            ValueError: If either scenario doesn't exist or if this creates a cycle
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get child scenario
        cursor.execute("SELECT id FROM scenarios WHERE name = ?", (child_name,))
        child_row = cursor.fetchone()
        if not child_row:
            conn.close()
            raise ValueError(f"Child scenario '{child_name}' does not exist")
        child_id = child_row["id"]

        # Get parent scenario
        cursor.execute("SELECT id FROM scenarios WHERE name = ?", (parent_name,))
        parent_row = cursor.fetchone()
        if not parent_row:
            conn.close()
            raise ValueError(f"Parent scenario '{parent_name}' does not exist")
        parent_id = parent_row["id"]

        # Check for cycles (prevent setting a scenario's ancestor as its child)
        # Get all ancestors of the child
        cursor.execute(
            """
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_id
                FROM scenarios
                WHERE id = ?
                
                UNION ALL
                
                SELECT s.id, s.parent_id
                FROM scenarios s
                INNER JOIN ancestors a ON s.id = a.parent_id
            )
            SELECT id FROM ancestors WHERE id = ?
        """,
            (child_id, parent_id),
        )

        if cursor.fetchone():
            conn.close()
            raise ValueError(
                f"Cannot set '{parent_name}' as parent of '{child_name}': "
                f"this would create a circular reference"
            )

        # Update the parent relationship
        cursor.execute(
            "UPDATE scenarios SET parent_id = ? WHERE id = ?", (parent_id, child_id)
        )

        conn.commit()
        conn.close()

    def set_active_scenario(self, user_id: str, scenario_id: Optional[int]) -> None:
        """
        Set the active scenario for a user.

        Args:
            user_id: User identifier
            scenario_id: Scenario ID to activate, or None to clear
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_scenario_id, last_interaction_time)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET active_scenario_id = excluded.active_scenario_id
        """,
            (user_id, scenario_id),
        )

        conn.commit()
        conn.close()

    def get_active_scenario(self, user_id: str) -> Optional[Scenario]:
        """
        Get the active scenario for a user.

        Args:
            user_id: User identifier

        Returns:
            Active Scenario object or None if not set
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT s.id, s.name, s.description, s.parent_id
            FROM user_state us
            INNER JOIN scenarios s ON us.active_scenario_id = s.id
            WHERE us.user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return Scenario(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                parent_id=row["parent_id"],
            )
        return None

    def list_all_scenarios(self) -> List[Scenario]:
        """
        List all scenarios in the system.

        Returns:
            List of all Scenario objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, description, parent_id 
            FROM scenarios 
            ORDER BY name
        """
        )

        rows = cursor.fetchall()
        conn.close()

        scenarios = []
        for row in rows:
            scenarios.append(
                Scenario(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    parent_id=row["parent_id"],
                )
            )

        return scenarios

    def delete_scenario(self, name: str) -> None:
        """
        Delete a scenario. Children will have their parent_id set to NULL.

        Args:
            name: Name of the scenario to delete
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM scenarios WHERE name = ?", (name,))

        conn.commit()
        conn.close()

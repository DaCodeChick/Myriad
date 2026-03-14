"""
Add Knowledge tool - Stores facts in the knowledge graph.

Part of RDSSC Phase 7: Modularized tool system.
"""

from typing import Dict, Any
from core.tools.base import Tool


class AddKnowledgeTool(Tool):
    """Tool for storing facts in the knowledge graph as entity-relationship triplets."""

    @property
    def name(self) -> str:
        return "add_knowledge"

    @property
    def description(self) -> str:
        return "Permanently store important facts about the user, yourself, or the world as a knowledge graph relationship. Use this when you learn meaningful information that should be remembered long-term. Examples: user preferences, facts about people, relationships between concepts."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity1": {
                    "type": "string",
                    "description": "The first entity (subject) - e.g., 'Bob', 'Python', 'Coffee'",
                },
                "entity1_type": {
                    "type": "string",
                    "description": "Type/category of entity1 - e.g., 'User', 'Language', 'Beverage', 'Concept', 'Person'",
                },
                "relation": {
                    "type": "string",
                    "description": "The relationship type - e.g., 'LIKES', 'KNOWS', 'CREATED', 'WORKS_WITH', 'DISLIKES'",
                },
                "entity2": {
                    "type": "string",
                    "description": "The second entity (object) - e.g., 'Gentle Possession', 'Django', 'Morning'",
                },
                "entity2_type": {
                    "type": "string",
                    "description": "Type/category of entity2 - e.g., 'Concept', 'Framework', 'TimeOfDay'",
                },
            },
            "required": [
                "entity1",
                "entity1_type",
                "relation",
                "entity2",
                "entity2_type",
            ],
        }

    def can_execute(self) -> bool:
        """This tool requires graph_memory to be available."""
        return self.context.graph_memory is not None

    def execute(
        self,
        entity1: str,
        entity1_type: str,
        relation: str,
        entity2: str,
        entity2_type: str,
    ) -> Dict[str, Any]:
        """
        Add a knowledge graph relationship.

        Args:
            entity1: Source entity name
            entity1_type: Source entity type
            relation: Relationship type
            entity2: Target entity name
            entity2_type: Target entity type

        Returns:
            Dictionary with success status and description
        """
        if not self.context.graph_memory:
            raise RuntimeError("Knowledge graph is not enabled")

        success = self.context.graph_memory.add_relationship(
            entity1, entity1_type, relation, entity2, entity2_type
        )

        if success:
            return {
                "status": "success",
                "description": f"Stored: {entity1} ({entity1_type}) {relation} {entity2} ({entity2_type})",
                "entity1": entity1,
                "relation": relation,
                "entity2": entity2,
            }
        else:
            raise RuntimeError("Failed to store knowledge relationship")

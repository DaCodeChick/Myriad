"""
Add Knowledge tool - Stores facts in the knowledge graph.

Part of RDSSC Phase 7: Modularized tool system.
Updated for Automated Discretion Engine: scope-based memory routing.
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
        return """Permanently store important facts about the user, yourself, or the world as a knowledge graph relationship. Use this when you learn meaningful information that should be remembered long-term.

AUTOMATED DISCRETION ENGINE - SCOPE SELECTION:
When saving a memory, you MUST choose its scope:
• 'isolated': Use for deeply private secrets, relationship dynamics specific to YOUR current persona, inside jokes between you and the user, romantic/intimate details, or information the user explicitly wants kept private from other personas.
• 'global': Use for general user facts, preferences (favorite food, schedule, allergies), world-state information, or anything that EVERY persona should know about the user.

IMPORTANCE SCORING (1-10):
• 1-3: Trivial/casual information (favorite color, small talk preferences)
• 4-6: Standard facts (work, hobbies, general interests) [DEFAULT]
• 7-9: Significant information (personal values, boundaries, major life events)
• 10: CORE ANCHORS (trauma, hard limits, life-or-death information, severe triggers)

Examples:
- User likes coffee: scope='global', importance_score=4
- User has severe allergy to peanuts: scope='global', importance_score=10
- User confided a secret only to you: scope='isolated', importance_score=7
- User's work schedule: scope='global', importance_score=5
- Intimate nickname user gave you: scope='isolated', importance_score=6
- User has PTSD from car accidents: scope='global', importance_score=10"""

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
                "scope": {
                    "type": "string",
                    "enum": ["isolated", "global"],
                    "description": "Memory scope: 'isolated' for persona-private memories, 'global' for hive-mind shared memories. Default: 'isolated'",
                    "default": "isolated",
                },
                "importance_score": {
                    "type": "integer",
                    "description": "Importance rating (1-10). 1-3: trivial, 4-6: standard, 7-9: significant, 10: critical/trauma. Default: 5",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
            },
            "required": [
                "entity1",
                "entity1_type",
                "relation",
                "entity2",
                "entity2_type",
                "scope",
            ],
        }

    def can_execute(self) -> bool:
        """This tool requires graph_memory and user context to be available."""
        return (
            self.context.graph_memory is not None
            and self.context.current_user_id is not None
            and self.context.current_persona_id is not None
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Add a knowledge graph relationship with scope-based routing.

        Args:
            entity1: Source entity name
            entity1_type: Source entity type
            relation: Relationship type
            entity2: Target entity name
            entity2_type: Target entity type
            scope: Memory scope ('isolated' or 'global')
            importance_score: Importance rating 1-10 (default: 5)

        Returns:
            Dictionary with success status and description
        """
        entity1 = kwargs.get("entity1")
        entity1_type = kwargs.get("entity1_type")
        relation = kwargs.get("relation")
        entity2 = kwargs.get("entity2")
        entity2_type = kwargs.get("entity2_type")
        scope = kwargs.get("scope", "isolated")
        importance_score = kwargs.get("importance_score", 5)

        if not self.context.graph_memory:
            raise RuntimeError("Knowledge graph is not enabled")

        if not self.context.current_user_id or not self.context.current_persona_id:
            raise RuntimeError("User/persona context not available")

        # Validate scope
        if scope not in ("isolated", "global"):
            scope = "isolated"  # Default to isolated for safety

        success = self.context.graph_memory.add_relationship(
            entity1=entity1,
            entity1_type=entity1_type,
            relation=relation,
            entity2=entity2,
            entity2_type=entity2_type,
            importance_score=importance_score,
            user_id=self.context.current_user_id,
            persona_id=self.context.current_persona_id,
            scope=scope,
        )

        scope_label = "GLOBAL (shared)" if scope == "global" else "ISOLATED (private)"

        if success:
            return {
                "status": "success",
                "description": f"Stored [{scope_label}]: {entity1} ({entity1_type}) {relation} {entity2} ({entity2_type}) [importance: {importance_score}]",
                "entity1": entity1,
                "relation": relation,
                "entity2": entity2,
                "scope": scope,
                "importance_score": importance_score,
            }
        else:
            raise RuntimeError("Failed to store knowledge relationship")

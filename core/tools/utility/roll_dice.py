"""
Roll Dice tool - Rolls a dice with specified number of sides.

Part of RDSSC Phase 7: Modularized tool system.
"""

import random
from typing import Dict, Any
from core.tools.base import Tool


class RollDiceTool(Tool):
    """Tool for rolling dice with a specified number of sides."""

    @property
    def name(self) -> str:
        return "roll_dice"

    @property
    def description(self) -> str:
        return "Roll a dice with a specified number of sides. Returns a random number between 1 and the number of sides (inclusive)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sides": {
                    "type": "integer",
                    "description": "The number of sides on the dice (e.g., 6 for a standard dice, 20 for a D20)",
                    "minimum": 2,
                    "maximum": 1000,
                }
            },
            "required": ["sides"],
        }

    def execute(self, sides: int) -> Dict[str, Any]:
        """
        Roll a dice with the specified number of sides.

        Args:
            sides: Number of sides on the dice

        Returns:
            Dictionary with roll result and sides
        """
        result = random.randint(1, sides)
        return {
            "result": result,
            "sides": sides,
            "message": f"🎲 Rolled a D{sides} and got: {result}",
        }

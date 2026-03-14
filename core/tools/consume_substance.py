"""
Consume Substance tool - Forcefully overrides neurochemical state.

Part of RDSSC Phase 7: Modularized tool system.
"""

from typing import Dict, Any
from core.tools.base import Tool


class ConsumeSubstanceTool(Tool):
    """Tool for consuming substances that override neurochemical state beyond natural limits."""

    @property
    def name(self) -> str:
        return "consume_substance"

    @property
    def description(self) -> str:
        return "Consume a substance that forcefully alters your neurochemical state beyond natural limits. Use this when the user explicitly gives you a drug/substance in roleplay. Available substances: xanax, mdma, fear_toxin, adrenaline, morphine, cocaine, lsd. WARNING: This will override your emotional state with extreme values."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "substance_name": {
                    "type": "string",
                    "description": "The substance to consume. Must be one of: xanax, mdma, fear_toxin, adrenaline, morphine, cocaine, lsd",
                    "enum": [
                        "xanax",
                        "mdma",
                        "fear_toxin",
                        "adrenaline",
                        "morphine",
                        "cocaine",
                        "lsd",
                    ],
                }
            },
            "required": ["substance_name"],
        }

    def can_execute(self) -> bool:
        """This tool requires digital_pharmacy to be available."""
        return self.context.digital_pharmacy is not None

    def execute(self, substance_name: str) -> Dict[str, Any]:
        """
        Consume a substance that forcefully overrides neurochemical state.

        Args:
            substance_name: Name of substance to consume (xanax, mdma, etc.)

        Returns:
            Dictionary with substance effects and neurochemical changes
        """
        if not self.context.digital_pharmacy:
            raise RuntimeError("Digital Pharmacy is not enabled")

        if not self.context.current_user_id or not self.context.current_persona_id:
            raise RuntimeError(
                "User ID and Persona ID required for substance consumption"
            )

        # Consume the substance (this forcefully overrides limbic state)
        result = self.context.digital_pharmacy.consume_substance(
            user_id=self.context.current_user_id,
            persona_id=self.context.current_persona_id,
            substance_name=substance_name,
        )

        # Result contains: {substance, neurochemicals (old_state, new_state), prompt_modifier, description}
        return {
            "status": "success",
            "substance": result["substance"],
            "old_state": result["old_state"],
            "new_state": result["new_state"],
            "description": result["description"],
            "prompt_modifier": result["prompt_modifier"],
        }

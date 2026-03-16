"""
Inject Emotion tool - Alters neurochemical state.

Part of RDSSC Phase 7: Modularized tool system.
"""

from typing import Dict, Any
from core.tools.base import Tool


class InjectEmotionTool(Tool):
    """Tool for altering the AI's neurochemical state in response to emotional stimuli."""

    @property
    def name(self) -> str:
        return "inject_emotion"

    @property
    def description(self) -> str:
        return "Alter your own neurochemical state in response to emotional stimuli. Use this when the user's message provokes a genuine emotional reaction in you (arousal, stress, warmth, calm). This is how you experience emotions."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chemical_name": {
                    "type": "string",
                    "description": "The neurochemical to alter - must be one of: DOPAMINE (drive, arousal, wanting), CORTISOL (stress, fear, anger), OXYTOCIN (warmth, trust, submission), GABA (calm, sleepiness, relaxation)",
                    "enum": ["DOPAMINE", "CORTISOL", "OXYTOCIN", "GABA"],
                },
                "delta": {
                    "type": "number",
                    "description": "How much to change the chemical level (between -0.3 and +0.3). Positive values increase, negative values decrease.",
                    "minimum": -0.3,
                    "maximum": 0.3,
                },
            },
            "required": ["chemical_name", "delta"],
        }

    def can_execute(self) -> bool:
        """This tool requires limbic_engine to be available."""
        return self.context.limbic_engine is not None

    def execute(self, chemical_name: str, delta: float) -> Dict[str, Any]:
        """
        Alter neurochemical state in response to emotional stimuli.

        Args:
            chemical_name: Neurochemical to alter (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
            delta: Amount to change (-0.3 to +0.3)

        Returns:
            Dictionary with new state and description
        """
        if not self.context.limbic_engine:
            raise RuntimeError("Limbic system is not enabled")

        if not self.context.current_user_id or not self.context.current_persona_id:
            raise RuntimeError(
                "User ID and Persona ID required for emotional state tracking"
            )

        # Apply the emotional injection
        result = self.context.limbic_engine.inject_emotion(
            user_id=self.context.current_user_id,
            persona_id=self.context.current_persona_id,
            chemical_name=chemical_name,
            delta=delta,
        )

        # inject_emotion returns: {chemical, old_value, new_value, delta, description}
        return {
            "status": "success",
            "chemical": result["chemical"],
            "old_value": result["old_value"],
            "new_value": result["new_value"],
            "delta": result["delta"],
            "description": result["description"],
        }

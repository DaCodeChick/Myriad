"""
Roleplay Feature - Consolidates all roleplay-specific components.

This feature module includes:
- Persona management (PersonaLoader, PersonaManager)
- Limbic system (emotional simulation)
- Digital Pharmacy (substance effects)
- Cadence degradation (text corruption)
- Metacognition (internal monologue)
- Lives & Save States (memory persistence)
- User Masks (user-side personas)
- Scenario Engine (world contexts)
- Session Notes (meta-level context)
"""

from typing import Any, Dict, Optional, List
from core.features.base_feature import BaseFeature
from core.features.roleplay.persona import PersonaLoader, PersonaCartridge
from core.features.roleplay.persona_manager import PersonaManager
from core.features.roleplay.limbic_engine import LimbicEngine
from core.features.roleplay.limbic_modifiers import DigitalPharmacy
from core.features.roleplay.cadence_degrader import CadenceDegrader
from core.features.roleplay.metacognition_engine import MetacognitionEngine
from core.features.roleplay.lives_engine import LivesEngine
from core.features.roleplay.save_states_engine import SaveStatesEngine
from core.features.roleplay.user_masks import UserMaskManager
from core.features.roleplay.user_state import UserStateManager
from core.features.roleplay.scenario import ScenarioEngine
from core.features.roleplay.session_notes import SessionNotesManager
from core.features.roleplay.mode_manager import ModeManager


class RoleplayFeature(BaseFeature):
    """
    Roleplay feature - manages persona-based interactions with emotional simulation,
    text degradation, internal monologue, and world contexts.
    """

    @property
    def name(self) -> str:
        return "roleplay"

    def __init__(self, config: Any, db_path: str, personas_dir: str = "personas"):
        """
        Initialize the roleplay feature.

        Args:
            config: Roleplay-specific configuration
            db_path: Main database path
            personas_dir: Directory containing persona JSON files
        """
        super().__init__(config, db_path)
        self.personas_dir = personas_dir

        # These will be initialized in initialize()
        self.persona_loader = None
        self.persona_manager = None
        self.user_state = None
        self.limbic_engine = None
        self.digital_pharmacy = None
        self.cadence_degrader = None
        self.metacognition_engine = None
        self.lives_engine = None
        self.save_states_engine = None
        self.user_mask_manager = None
        self.scenario_engine = None
        self.session_notes = None
        self.mode_manager = None

    def initialize(self, **dependencies) -> None:
        """
        Initialize all roleplay components.

        Args:
            **dependencies: Expected keys:
                - memory_matrix: MemoryMatrix instance
                - vision_service: Optional VisionCacheService
        """
        memory_matrix = dependencies.get("memory_matrix")
        vision_service = dependencies.get("vision_service")

        print("🎭 Initializing Roleplay Feature...")

        # User State (Active Persona Tracking)
        # RDSSC Phase 3: Initialize user_state first, use instead of memory_matrix for persona tracking
        self.user_state = UserStateManager(db_path=self.db_path)

        # Persona System
        self.persona_loader = PersonaLoader(
            personas_dir=self.personas_dir,
            db_path=self.db_path,
            vision_service=vision_service,
        )
        self.persona_manager = PersonaManager(
            persona_loader=self.persona_loader,
            user_state=self.user_state,
        )

        # Limbic System (Emotional Neurochemistry)
        self.limbic_engine = LimbicEngine(db_path=self.db_path)
        self.digital_pharmacy = DigitalPharmacy(self.limbic_engine)

        # Cadence Degradation (Text Post-Processing)
        self.cadence_degrader = CadenceDegrader()

        # Metacognition (Internal Monologue)
        self.metacognition_engine = MetacognitionEngine(db_path=self.db_path)

        # Lives & Save States (Memory Persistence)
        self.lives_engine = LivesEngine(db_path=self.db_path)
        self.save_states_engine = SaveStatesEngine(db_path=self.db_path)

        # User Masks (User-Side Personas)
        self.user_mask_manager = UserMaskManager(
            db_path=self.db_path, persona_loader=self.persona_loader
        )

        # Scenario Engine (World Tree)
        self.scenario_engine = ScenarioEngine(
            db_path=self.db_path,
            vision_service=vision_service,
        )

        # Session Notes (Meta-Level Context)
        self.session_notes = SessionNotesManager(db_path=self.db_path)

        # Mode Manager (Behavioral Overrides - OOC, HENTAI, etc.)
        self.mode_manager = ModeManager(db_path=self.db_path)

        print("   ✓ Persona system loaded")
        print("   ✓ Limbic & pharmacy initialized")
        print("   ✓ Metacognition enabled")
        print("   ✓ Lives & save states ready")
        print("   ✓ User masks & scenarios loaded")
        print("   ✓ Mode manager initialized")

    # ========================
    # PERSONA MANAGEMENT
    # ========================

    def get_active_personas(self, user_id: str) -> List[PersonaCartridge]:
        """Get all active personas for a user (Ensemble Mode)."""
        return self.persona_manager.get_active_personas(user_id)

    def get_active_persona(self, user_id: str) -> Optional[PersonaCartridge]:
        """Get first active persona (legacy single-persona mode)."""
        return self.persona_manager.get_active_persona(user_id)

    def add_active_persona(self, user_id: str, persona_id: str) -> bool:
        """Add persona to active ensemble."""
        return self.persona_manager.add_active_persona(user_id, persona_id)

    def remove_active_persona(self, user_id: str, persona_id: str) -> bool:
        """Remove persona from active ensemble."""
        return self.persona_manager.remove_active_persona(user_id, persona_id)

    def clear_active_personas(self, user_id: str) -> None:
        """Clear all active personas."""
        self.persona_manager.clear_active_personas(user_id)

    def switch_persona(self, user_id: str, persona_id: str) -> bool:
        """Switch to single persona (legacy mode)."""
        return self.persona_manager.switch_persona(user_id, persona_id)

    def list_personas(self) -> List[str]:
        """List all available persona IDs."""
        return self.persona_manager.list_personas()

    # ========================
    # CONTEXT INJECTION
    # ========================

    def inject_context(
        self, user_id: str, base_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Inject roleplay-specific context (personas, limbic state, scenarios, etc.)
        into the conversation context.
        """
        # This will be called by ConversationContextBuilder
        # We'll pass roleplay components to the context builder
        base_context["roleplay"] = {
            "limbic_engine": self.limbic_engine,
            "digital_pharmacy": self.digital_pharmacy,
            "metacognition_engine": self.metacognition_engine,
            "user_mask_manager": self.user_mask_manager,
            "scenario_engine": self.scenario_engine,
            "session_notes": self.session_notes,
        }
        return base_context

    # ========================
    # POST-PROCESSING
    # ========================

    def post_process_response(
        self, user_id: str, response: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Post-process response with cadence degradation if enabled.

        Args:
            user_id: User identifier
            response: Raw LLM response
            metadata: Should contain 'user_preferences' and 'persona_id'
        """
        user_preferences = metadata.get("user_preferences", {})
        persona_id = metadata.get("persona_id")

        # Apply cadence degradation if enabled
        if user_preferences.get("cadence_enabled", False) and persona_id:
            persona = self.persona_loader.get_persona(persona_id)
            if persona:
                response = self.cadence_degrader.degrade(
                    text=response,
                    persona_cartridge=persona,
                    limbic_engine=self.limbic_engine,
                    user_id=user_id,
                )

        return response

    # ========================
    # HOOKS
    # ========================

    def on_message_end(self, user_id: str, response: str) -> None:
        """
        Called after response generation - handle metacognition archiving if enabled.
        """
        # Metacognition archiving happens in MessageProcessor
        # This hook is available for future extensions
        pass

    def cleanup(self) -> None:
        """Cleanup roleplay resources."""
        print("🎭 Unloading Roleplay Feature...")

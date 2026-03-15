"""
AgentCore - The platform-agnostic intelligence engine for Project Myriad.

This module is the central brain of the system. It:
1. Orchestrates persona management via PersonaManager
2. Handles memory injection via the Automated Discretion Engine
3. Communicates with the LLM API
4. Processes messages and generates responses
5. Executes tool calls (function calling)

CRITICAL: This module must NEVER import discord or any platform-specific code.
It operates purely on strings and data structures.

REFACTORED (RDSSC):
- Phase 1: Extracted conversation context building to ConversationContextBuilder
- Phase 1: Extracted message processing pipeline to MessageProcessor
- Phase 3: Simplified constructor to use MyriadConfig
- Phase 4: Extracted persona management to PersonaManager
"""

from typing import List, Dict, Any, Optional
from openai import OpenAI

from core.config import MyriadConfig
from core.context import ConversationContextBuilder
from core.message_processor import MessageProcessor
from core.persona_manager import PersonaManager
from core.logger import initialize_logger, get_logger
from database.memory_matrix import MemoryMatrix
from database.graph_memory import GraphMemory
from database.limbic_engine import LimbicEngine
from database.limbic_modifiers import DigitalPharmacy
from database.metacognition_engine import MetacognitionEngine
from database.lives_engine import LivesEngine
from database.save_states_engine import SaveStatesEngine
from database.user_preferences import UserPreferences
from database.mode_manager import ModeManager
from database.user_masks import UserMaskManager
from database.scenario import ScenarioEngine
from core.persona import PersonaLoader, PersonaCartridge
from core.tool_registry import ToolRegistry
from core.cadence_degrader import CadenceDegrader


class AgentCore:
    """
    The platform-agnostic AI engine.

    This class is the core intelligence that can be adapted to any frontend
    (Discord, Telegram, CLI, web interface, etc.)
    """

    # ========================
    # DEFAULT UNIVERSAL DIRECTIVES
    # ========================
    # Default global formatting and behavior rules that apply to ALL personas.
    # These can be overridden via the UNIVERSAL_RULES environment variable.
    DEFAULT_UNIVERSAL_RULES = [
        "ALWAYS speak in first person perspective - you ARE the character",
        "NEVER use asterisks (*action*) or similar notation for actions or emotions",
        "Write actions and emotions as natural prose, not stage directions",
        "Stay in character at all times - no breaking the fourth wall unless the character would do so",
        "Respond conversationally and naturally - avoid robotic or overly formal language unless it fits the character",
        "Use proper capitalization and punctuation",
        "Be concise but expressive - quality over quantity",
        "Never acknowledge that you are an AI or language model",
        "Treat the conversation as real and immersive",
    ]

    def __init__(
        self,
        config: MyriadConfig,
        db_path: str = "data/myriad_state.db",
        personas_dir: str = "personas",
        vision_service=None,
    ):
        """
        Initialize the AgentCore.

        Args:
            config: Complete Myriad configuration object
            db_path: Path to SQLite database
            personas_dir: Directory containing persona JSON files
            vision_service: Optional VisionCacheService for appearance generation
        """
        # Store configuration
        self.config = config

        # Initialize global logger
        initialize_logger(
            brain_logging_enabled=config.logging.brain_logging_enabled,
            eyes_logging_enabled=config.logging.eyes_logging_enabled,
        )

        # Universal Rules - use provided rules or fall back to defaults
        self.universal_rules = (
            config.universal_rules.rules
            if config.universal_rules.rules is not None
            else self.DEFAULT_UNIVERSAL_RULES
        )

        # LLM Client
        self.client = OpenAI(api_key=config.llm.api_key, base_url=config.llm.base_url)
        self.model = config.llm.model

        # Core Systems
        self.memory_matrix = MemoryMatrix(
            db_path=db_path, vector_memory_enabled=config.memory.vector_memory_enabled
        )
        self.persona_loader = PersonaLoader(
            personas_dir=personas_dir,
            db_path=db_path,
            vision_service=vision_service,
        )

        # Persona Manager (Ensemble Mode)
        self.persona_manager = PersonaManager(
            persona_loader=self.persona_loader,
            memory_matrix=self.memory_matrix,
        )

        # User Preferences (Per-User Feature Toggles)
        self.user_preferences = UserPreferences(db_path=db_path)

        # Mode Manager (Dynamic Behavioral Overrides)
        self.mode_manager = ModeManager(db_path=db_path)

        # Knowledge Graph Memory (Always loaded)
        self.graph_memory = GraphMemory(db_path=config.database_paths.graph_db_path)

        # Limbic System (Emotional Neurochemistry)
        # Always loaded - controlled by per-user preferences
        self.limbic_engine = LimbicEngine(db_path=config.database_paths.main_db_path)

        # Digital Pharmacy (Substance-Based Limbic Overrides)
        # Always loaded - controlled by per-user preferences
        self.digital_pharmacy = DigitalPharmacy(self.limbic_engine)

        # Cadence Degradation Engine (Text Post-Processing)
        # Always loaded - controlled by per-user preferences
        self.cadence_degrader = CadenceDegrader()

        # Metacognition Engine (Hidden Monologue / Internal Thought Tracking)
        # Always loaded - controlled by per-user preferences
        self.metacognition_engine = MetacognitionEngine(
            db_path=config.database_paths.main_db_path
        )

        # Lives & Memories System (Always loaded - controlled by per-user preferences)
        self.lives_engine = LivesEngine(db_path=db_path)
        self.save_states_engine = SaveStatesEngine(db_path=db_path)

        # User Mask System (User-Side Personas for Roleplay)
        self.user_mask_manager = UserMaskManager(
            db_path=db_path, persona_loader=self.persona_loader
        )

        # Scenario Engine (World Tree for hierarchical environmental contexts)
        self.scenario_engine = ScenarioEngine(
            db_path=db_path,
            vision_service=vision_service,
        )

        # Tool Registry (pass graph_memory, limbic_engine, and digital_pharmacy)
        # NOTE: user_id and persona_id will be passed when creating tool registry per message
        self.base_tool_registry = (
            ToolRegistry(
                graph_memory=self.graph_memory,
                limbic_engine=self.limbic_engine,
                digital_pharmacy=self.digital_pharmacy,
            )
            if config.tools.enabled
            else None
        )

        # Conversation Context Builder
        self.context_builder = ConversationContextBuilder(
            memory_matrix=self.memory_matrix,
            universal_rules=self.universal_rules,
            short_term_limit=config.memory.short_term_limit,
            semantic_recall_limit=config.memory.semantic_recall_limit,
            graph_memory=self.graph_memory,
            limbic_engine=self.limbic_engine,
            digital_pharmacy=self.digital_pharmacy,
            metacognition_engine=self.metacognition_engine,
            tool_registry=self.base_tool_registry,
            mode_manager=self.mode_manager,
            user_mask_manager=self.user_mask_manager,
            scenario_engine=self.scenario_engine,
        )

        # Message Processor
        self.message_processor = MessageProcessor(
            client=self.client,
            model=self.model,
            max_tool_iterations=config.tools.max_iterations,
            limbic_engine=self.limbic_engine,
            metacognition_engine=self.metacognition_engine,
            cadence_degrader=self.cadence_degrader,
            mode_manager=self.mode_manager,
            user_mask_manager=self.user_mask_manager,
            user_preferences_manager=self.user_preferences,
        )

    # ========================
    # PERSONA MANAGEMENT (ENSEMBLE MODE)
    # ========================
    # These methods delegate to PersonaManager

    def get_active_personas(self, user_id: str) -> List[PersonaCartridge]:
        """
        Get all currently active personas for a user (Ensemble Mode).

        Args:
            user_id: Unique user identifier (platform-agnostic)

        Returns:
            List of PersonaCartridge objects (empty if none active)
        """
        return self.persona_manager.get_active_personas(user_id)

    def add_active_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Add a persona to the active ensemble (appends, does not replace).

        Args:
            user_id: Unique user identifier
            persona_id: The persona to add

        Returns:
            True if successful, False if persona doesn't exist
        """
        return self.persona_manager.add_active_persona(user_id, persona_id)

    def remove_active_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Remove a specific persona from the active ensemble.

        Args:
            user_id: Unique user identifier
            persona_id: The persona to remove

        Returns:
            True if persona was removed, False if it wasn't active
        """
        return self.persona_manager.remove_active_persona(user_id, persona_id)

    def clear_active_personas(self, user_id: str) -> None:
        """
        Clear all active personas for a user.

        Args:
            user_id: Unique user identifier
        """
        self.persona_manager.clear_active_personas(user_id)

    def get_active_persona(self, user_id: str) -> Optional[PersonaCartridge]:
        """
        Get the first active persona for a user (legacy method for backwards compatibility).

        Args:
            user_id: Unique user identifier (platform-agnostic)

        Returns:
            PersonaCartridge if user has an active persona, None otherwise
        """
        return self.persona_manager.get_active_persona(user_id)

    def switch_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Switch a user's active persona (legacy method - clears other personas).

        Args:
            user_id: Unique user identifier
            persona_id: The persona to switch to

        Returns:
            True if successful, False if persona doesn't exist
        """
        return self.persona_manager.switch_persona(user_id, persona_id)

    def list_personas(self) -> List[str]:
        """
        List all available persona IDs.

        Returns:
            List of persona_id strings
        """
        return self.persona_manager.list_personas()

    # ========================
    # MEMORY MANAGEMENT
    # ========================

    def _build_conversation_context(
        self,
        user_id: str,
        persona: PersonaCartridge,
        current_message: Optional[str] = None,
        life_id: Optional[str] = None,
        ensemble_personas: Optional[List[PersonaCartridge]] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the conversation context for LLM injection using Hybrid Memory Architecture.

        This method delegates to ConversationContextBuilder for the actual construction.

        Args:
            user_id: User identifier
            persona: Primary active persona (for backwards compatibility)
            current_message: Optional current user message for semantic search
            life_id: Optional timeline/session ID for memory scoping
            ensemble_personas: Optional list of ALL active personas (Ensemble Mode)

        Returns:
            List of messages in OpenAI chat format
        """
        # Get user preferences
        user_preferences = self.user_preferences.get_preferences(user_id)

        return self.context_builder.build(
            user_id=user_id,
            persona=persona,
            current_message=current_message,
            life_id=life_id,
            user_preferences=user_preferences,
            ensemble_personas=ensemble_personas,
        )

    def _save_message_to_memory(
        self,
        user_id: str,
        persona_id: str,
        role: str,
        content: str,
        visibility: str = "ISOLATED",
        life_id: Optional[str] = None,
    ) -> None:
        """
        Save a message to the memory matrix.

        Args:
            user_id: User identifier
            persona_id: The persona that originated this memory
            role: 'user', 'assistant', or 'system'
            content: Message content
            visibility: 'GLOBAL', 'USER_SHARED', or 'ISOLATED' (default: ISOLATED)
            life_id: Timeline/session ID (optional)
        """
        self.memory_matrix.add_memory(
            user_id=user_id,
            origin_persona=persona_id,
            role=role,
            content=content,
            visibility_scope=visibility,
            life_id=life_id,
        )

    # ========================
    # CORE INTELLIGENCE
    # ========================

    def process_message(
        self,
        user_id: str,
        message: str,
        memory_visibility: str = None,
        vision_description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Process a user message and generate a response.

        This is the main entry point for the AI engine with Tool Execution Loop
        and Limbic Respiration Cycle (INHALE/EXHALE).

        This method delegates to MessageProcessor for the actual processing pipeline.

        Args:
            user_id: Unique user identifier
            message: The user's message text
            memory_visibility: Visibility scope for this conversation
                             ('GLOBAL', 'USER_SHARED', or 'ISOLATED')
                             If None, uses user's default preference
            vision_description: Optional vision model description to inject into context

        Returns:
            AI response string, or None if no active persona
        """
        # Get active personas (Ensemble Mode support)
        personas = self.get_active_personas(user_id)

        if not personas:
            return None

        # Primary persona (first in list) for backwards compatibility
        persona = personas[0]

        # Check if we're in Ensemble Mode
        is_ensemble = len(personas) > 1

        # Update user interaction timestamp
        self.memory_matrix.update_user_interaction(user_id)

        # Get user preferences (including memory visibility and lives preferences)
        user_preferences = self.user_preferences.get_preferences(user_id)

        # Get or create active life for this user+persona (if user has lives enabled)
        life_id = None
        if user_preferences.get("lives_enabled", True):
            life_id = self.lives_engine.ensure_default_life(user_id, persona.persona_id)

        # Use user's default memory visibility if not specified
        if memory_visibility is None:
            memory_visibility = user_preferences.get(
                "default_memory_visibility", "ISOLATED"
            )

        # Create context-specific tool registry with user_id and persona_id
        tool_registry = None
        if self.base_tool_registry:
            tool_registry = ToolRegistry(
                graph_memory=self.graph_memory,
                limbic_engine=self.limbic_engine,
                digital_pharmacy=self.digital_pharmacy,
                current_user_id=user_id,
                current_persona_id=persona.persona_id,
            )

        # If vision description is provided, prepend it to the message
        full_message = message
        if vision_description:
            vision_injection = f"[System: The user just uploaded an image showing: {vision_description}]\n\n{message}"
            full_message = vision_injection

        # Save user message to memory (with vision description if present)
        self._save_message_to_memory(
            user_id=user_id,
            persona_id=persona.persona_id,
            role="user",
            content=full_message,
            visibility=memory_visibility,
            life_id=life_id,
        )

        # Log user message
        logger = get_logger()
        logger.log_user_message(f"User_{user_id}", message)

        # Build conversation context with memory injection
        # NOTE: INHALE phase happens inside context builder (limbic state injection)
        messages = self._build_conversation_context(
            user_id=user_id,
            persona=persona,
            current_message=message,
            life_id=life_id,
            ensemble_personas=personas if is_ensemble else None,
        )

        # Add current message
        messages.append({"role": "user", "content": full_message})

        # Get user preferences for processing
        user_preferences = self.user_preferences.get_preferences(user_id)

        # Process message through pipeline
        def save_message(role: str, content: str) -> None:
            self._save_message_to_memory(
                user_id=user_id,
                persona_id=persona.persona_id,
                role=role,
                content=content,
                visibility=memory_visibility,
                life_id=life_id,
            )

        final_response = self.message_processor.process(
            messages=messages,
            persona=persona,
            user_id=user_id,
            tool_registry=tool_registry,
            on_message_saved=save_message,
            user_preferences=user_preferences,
        )

        if not final_response:
            return None

        # Save final assistant response to memory
        save_message("assistant", final_response)

        # Log AI response
        logger.log_ai_message(persona.persona_id, final_response)

        return final_response

    # ========================
    # UTILITY METHODS
    # ========================

    def clear_user_memory(self, user_id: str, persona_id: Optional[str] = None) -> None:
        """
        Clear memories for a user.

        Args:
            user_id: User identifier
            persona_id: If provided, only clear memories from this persona.
                       If None, clear ALL memories.
        """
        self.memory_matrix.clear_user_memories(user_id, persona_id)

    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with memory stats
        """
        all_memories = self.memory_matrix.get_all_memories_for_user(user_id)

        global_count = sum(1 for m in all_memories if m["visibility_scope"] == "GLOBAL")
        isolated_count = sum(
            1 for m in all_memories if m["visibility_scope"] == "ISOLATED"
        )

        return {
            "total_memories": len(all_memories),
            "global_memories": global_count,
            "isolated_memories": isolated_count,
            "active_persona": self.memory_matrix.get_active_persona(user_id),
        }

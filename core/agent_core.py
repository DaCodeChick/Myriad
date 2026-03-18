"""
AgentCore - The platform-agnostic intelligence engine for Project Myriad.

This module is the central brain of the system. It:
1. Loads feature modules (roleplay, etc.) dynamically
2. Handles memory injection via the Automated Discretion Engine
3. Communicates with the LLM API via modular provider system
4. Processes messages and generates responses
5. Executes tool calls (function calling)

CRITICAL: This module must NEVER import discord or any platform-specific code.
It operates purely on strings and data structures.

REFACTORED (RDSSC):
- Phase 1: Extracted conversation context building to ConversationContextBuilder
- Phase 1: Extracted message processing pipeline to MessageProcessor
- Phase 3: Simplified constructor to use MyriadConfig
- Phase 4: Extracted persona management to PersonaManager
- Phase 5: Refactored to use modular provider system
- Phase 6: Refactored to use modular feature system (roleplay becomes optional)
"""

from typing import List, Dict, Any, Optional, Tuple, cast

from core.config import MyriadConfig
from core.providers import ProviderFactory
from core.context import ConversationContextBuilder
from core.message_processor import MessageProcessor
from core.logger import initialize_logger, get_logger
from core.init_logger import init_log
from database.memory_matrix import MemoryMatrix
from database.graph_memory import GraphMemory
from database.user_preferences import UserPreferences
from core.tool_registry import ToolRegistry

# Feature imports
from core.features import RoleplayFeature
from core.features.base_feature import BaseFeature


class AgentCore:
    """
    The platform-agnostic AI engine with modular feature system.

    This class is the core intelligence that can be adapted to any frontend
    (Discord, Telegram, CLI, web interface, etc.)

    Features (like roleplay) are loaded dynamically and can be enabled/disabled.
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
        db_path: str = "data/myriad_state.db",  # DEPRECATED - kept for backward compatibility
        personas_dir: str = "personas",
        vision_service=None,
        enable_roleplay: bool = True,  # Enable roleplay feature by default
    ):
        """
        Initialize the AgentCore with optional features.

        Args:
            config: Complete Myriad configuration object
            db_path: DEPRECATED - use config.database_paths instead
            personas_dir: Directory containing persona JSON files (for roleplay feature)
            vision_service: Optional VisionCacheService for appearance generation
            enable_roleplay: Enable the roleplay feature (personas, limbic, lives, etc.)
        """
        # Store configuration
        self.config = config

        # RDSSC Phase 1: Use feature-specific database paths from config
        # db_path is deprecated but kept for backward compatibility
        self.db_path = db_path  # Legacy - still used by some components

        # Initialize global logger
        initialize_logger(
            brain_console_enabled=config.logging.brain_console_enabled,
            eyes_console_enabled=config.logging.eyes_console_enabled,
            brain_file_enabled=config.logging.brain_file_enabled,
            eyes_file_enabled=config.logging.eyes_file_enabled,
            log_dir=config.logging.log_dir,
        )

        # Universal Rules - use provided rules or fall back to defaults
        self.universal_rules = (
            config.universal_rules.rules
            if config.universal_rules.rules is not None
            else self.DEFAULT_UNIVERSAL_RULES
        )

        # Initialize LLM Provider (modular provider system)
        print(f"\n🧠 Initializing LLM Provider: {config.llm.provider}")
        self.provider = ProviderFactory.create_provider(config.llm)
        print(f"   Model: {self.provider.model_name}")
        print(f"   Provider: {self.provider.provider_name}\n")

        # ====================
        # CORE INFRASTRUCTURE (always loaded)
        # ====================

        # Memory & User State (use memory_db_path)
        init_log.debug("→ Creating MemoryMatrix...")
        self.memory_matrix = MemoryMatrix(
            db_path=config.database_paths.memory_db_path,
            vector_memory_enabled=config.memory.vector_memory_enabled,
        )
        init_log.debug("✓ MemoryMatrix created")

        init_log.debug("→ Creating UserPreferences...")
        self.user_preferences = UserPreferences(
            db_path=config.database_paths.memory_db_path
        )
        init_log.debug("✓ UserPreferences created")

        # Knowledge Graph Memory (Always loaded)
        init_log.debug("→ Creating GraphMemory...")
        self.graph_memory = GraphMemory(db_path=config.database_paths.graph_db_path)
        init_log.debug("✓ GraphMemory created")

        # ====================
        # FEATURE SYSTEM (modular components)
        # ====================

        self.features: Dict[str, BaseFeature] = {}

        # Load Roleplay Feature (if enabled)
        init_log.debug(f"→ enable_roleplay={enable_roleplay}")
        if enable_roleplay:
            init_log.debug("→ Calling _load_roleplay_feature...")
            self._load_roleplay_feature(personas_dir, vision_service)
            init_log.debug("✓ _load_roleplay_feature returned")

        # Base Tool Registry (without roleplay-specific components)
        # Features can add their own tools via get_tools()
        init_log.debug("→ Getting roleplay feature from features dict...")
        roleplay_feature = cast(
            Optional[RoleplayFeature], self.features.get("roleplay")
        )
        init_log.debug(f"✓ roleplay_feature={roleplay_feature is not None}")

        # Collect feature tools (e.g., roleplay tools)
        feature_tools = []
        if roleplay_feature:
            init_log.debug("→ Importing ROLEPLAY_TOOLS...")
            from core.features.roleplay.tools import ROLEPLAY_TOOLS

            feature_tools.extend(ROLEPLAY_TOOLS)
            init_log.debug(f"✓ Loaded {len(ROLEPLAY_TOOLS)} roleplay tools")

        init_log.debug(
            f"→ Creating ToolRegistry (tools.enabled={config.tools.enabled})..."
        )
        self.base_tool_registry = (
            ToolRegistry(
                graph_memory=self.graph_memory,
                limbic_engine=roleplay_feature.limbic_engine
                if roleplay_feature
                else None,
                digital_pharmacy=roleplay_feature.digital_pharmacy
                if roleplay_feature
                else None,
                llm_provider=self.provider,
                feature_tools=feature_tools if feature_tools else None,
            )
            if config.tools.enabled
            else None
        )
        init_log.debug(
            f"✓ ToolRegistry created (enabled={self.base_tool_registry is not None})"
        )

        # ====================
        # CONTEXT & PROCESSING PIPELINES
        # ====================

        # Conversation Context Builder
        init_log.debug("→ Calling _init_context_builder...")
        self._init_context_builder()
        init_log.debug("✓ _init_context_builder returned")

        # Message Processor
        init_log.debug("→ Calling _init_message_processor...")
        self._init_message_processor()
        init_log.debug("✓ _init_message_processor returned")

        init_log.info("✓ AgentCore fully initialized!")

    def _load_roleplay_feature(self, personas_dir: str, vision_service) -> None:
        """Load the roleplay feature with all its components."""
        init_log.info("\n📦 Loading Roleplay Feature...")
        init_log.debug("  → Creating RoleplayFeature instance...")

        # RDSSC Phase 1: Use roleplay-specific database
        roleplay = RoleplayFeature(
            config=self.config,  # Pass full config for now
            db_path=self.config.database_paths.roleplay_db_path,
            personas_dir=personas_dir,
        )
        init_log.debug("  ✓ RoleplayFeature instance created")

        # Initialize with dependencies
        init_log.debug("  → Initializing RoleplayFeature with dependencies...")
        roleplay.initialize(
            memory_matrix=self.memory_matrix,
            vision_service=vision_service,
        )
        init_log.debug("  ✓ RoleplayFeature initialized")

        self.features["roleplay"] = roleplay

        # Convenience property for backward compatibility
        self.roleplay = roleplay
        init_log.info("✓ Roleplay Feature loaded\n")

    def _init_context_builder(self) -> None:
        """Initialize the conversation context builder with available features."""
        roleplay_feature = cast(
            Optional[RoleplayFeature], self.features.get("roleplay")
        )

        self.context_builder = ConversationContextBuilder(
            memory_matrix=self.memory_matrix,
            universal_rules=self.universal_rules,
            short_term_limit=self.config.memory.short_term_limit,
            semantic_recall_limit=self.config.memory.semantic_recall_limit,
            graph_memory=self.graph_memory,
            limbic_engine=roleplay_feature.limbic_engine if roleplay_feature else None,
            digital_pharmacy=roleplay_feature.digital_pharmacy
            if roleplay_feature
            else None,
            metacognition_engine=roleplay_feature.metacognition_engine
            if roleplay_feature
            else None,
            tool_registry=self.base_tool_registry,
            mode_manager=roleplay_feature.mode_manager if roleplay_feature else None,
            user_mask_manager=roleplay_feature.user_mask_manager
            if roleplay_feature
            else None,
            scenario_engine=roleplay_feature.scenario_engine
            if roleplay_feature
            else None,
            session_notes=roleplay_feature.session_notes if roleplay_feature else None,
            user_state_manager=roleplay_feature.user_state
            if roleplay_feature
            else None,
        )

    def _init_message_processor(self) -> None:
        """Initialize the message processor with available features."""
        roleplay_feature = cast(
            Optional[RoleplayFeature], self.features.get("roleplay")
        )

        self.message_processor = MessageProcessor(
            provider=self.provider,
            max_tool_iterations=self.config.tools.max_iterations,
            limbic_engine=roleplay_feature.limbic_engine if roleplay_feature else None,
            metacognition_engine=roleplay_feature.metacognition_engine
            if roleplay_feature
            else None,
            cadence_degrader=roleplay_feature.cadence_degrader
            if roleplay_feature
            else None,
            mode_manager=roleplay_feature.mode_manager if roleplay_feature else None,
            user_mask_manager=roleplay_feature.user_mask_manager
            if roleplay_feature
            else None,
            user_preferences_manager=self.user_preferences,
            session_notes=roleplay_feature.session_notes if roleplay_feature else None,
        )

    # ========================
    # PERSONA MANAGEMENT (delegated to roleplay feature)
    # ========================
    # These methods provide backward compatibility

    def get_active_personas(self, user_id: str):
        """Get active personas (requires roleplay feature)."""
        if "roleplay" not in self.features:
            raise RuntimeError("Roleplay feature not loaded - cannot use personas")
        roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
        return roleplay_feature.get_active_personas(user_id)

    def get_active_persona(self, user_id: str):
        """Get first active persona (requires roleplay feature)."""
        if "roleplay" not in self.features:
            raise RuntimeError("Roleplay feature not loaded - cannot use personas")
        roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
        return roleplay_feature.get_active_persona(user_id)

    def add_active_persona(self, user_id: str, persona_id: str) -> bool:
        """Add persona to ensemble (requires roleplay feature)."""
        if "roleplay" not in self.features:
            raise RuntimeError("Roleplay feature not loaded - cannot use personas")
        roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
        return roleplay_feature.add_active_persona(user_id, persona_id)

    def remove_active_persona(self, user_id: str, persona_id: str) -> bool:
        """Remove persona from ensemble (requires roleplay feature)."""
        if "roleplay" not in self.features:
            raise RuntimeError("Roleplay feature not loaded - cannot use personas")
        roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
        return roleplay_feature.remove_active_persona(user_id, persona_id)

    def clear_active_personas(self, user_id: str) -> None:
        """Clear all active personas (requires roleplay feature)."""
        if "roleplay" not in self.features:
            raise RuntimeError("Roleplay feature not loaded - cannot use personas")
        roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
        roleplay_feature.clear_active_personas(user_id)

    def switch_persona(self, user_id: str, persona_id: str) -> bool:
        """Switch to single persona (requires roleplay feature)."""
        logger = get_logger()
        logger.debug(
            f"AgentCore.switch_persona called: user_id={user_id}, persona_id={persona_id}"
        )
        if "roleplay" not in self.features:
            raise RuntimeError("Roleplay feature not loaded - cannot use personas")
        roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
        logger.debug("Calling roleplay_feature.switch_persona...")
        result = roleplay_feature.switch_persona(user_id, persona_id)
        logger.debug(f"roleplay_feature.switch_persona returned: {result}")
        return result

    def list_personas(self) -> List[str]:
        """List available personas (requires roleplay feature)."""
        if "roleplay" not in self.features:
            raise RuntimeError("Roleplay feature not loaded - cannot use personas")
        roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
        return roleplay_feature.list_personas()

    # ========================
    # MEMORY MANAGEMENT
    # ========================

    def _build_conversation_context(
        self,
        user_id: str,
        persona=None,  # Made optional for non-roleplay features
        current_message: Optional[str] = None,
        life_id: Optional[str] = None,
        ensemble_personas: Optional[List] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the conversation context for LLM injection using Hybrid Memory Architecture.

        This method delegates to ConversationContextBuilder for the actual construction.

        Args:
            user_id: User identifier
            persona: Primary active persona (optional, for roleplay feature)
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
        persona_id: Optional[str],  # Made optional for non-roleplay features
        role: str,
        content: str,
        visibility: str = "ISOLATED",
        life_id: Optional[str] = None,
    ) -> None:
        """
        Save a message to the memory matrix.

        Args:
            user_id: User identifier
            persona_id: The persona that originated this memory (optional)
            role: 'user', 'assistant', or 'system'
            content: Message content
            visibility: 'GLOBAL', 'USER_SHARED', or 'ISOLATED' (default: ISOLATED)
            life_id: Timeline/session ID (optional)
        """
        self.memory_matrix.add_memory(
            user_id=user_id,
            origin_persona=persona_id or "system",  # Default to "system" if no persona
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
        memory_visibility: Optional[str] = None,
        vision_description: Optional[str] = None,
        image_data: Optional[List[Tuple[bytes, str]]] = None,
    ) -> Tuple[Optional[str], List[Tuple[bytes, str]]]:
        """
        Process a user message and generate a response.

        This is the main entry point for the AI engine with Tool Execution Loop
        and optional Limbic Respiration Cycle (INHALE/EXHALE) if roleplay is enabled.

        This method delegates to MessageProcessor for the actual processing pipeline.

        Args:
            user_id: Unique user identifier
            message: The user's message text
            memory_visibility: Visibility scope for this conversation
                             ('GLOBAL', 'USER_SHARED', or 'ISOLATED')
                             If None, uses user's default preference
            vision_description: Optional vision model description to inject into context
            image_data: Optional list of (image_bytes, mime_type) tuples for native vision

        Returns:
            Tuple of (AI response string or None, list of generated images)
            Generated images are (image_bytes, mime_type) tuples from image generation tool
        """
        # Get active personas (only if roleplay feature is loaded)
        personas = []
        persona = None
        is_ensemble = False

        if "roleplay" in self.features:
            personas = self.get_active_personas(user_id)
            if not personas:
                return None, []  # Return empty images list
            persona = personas[0]
            is_ensemble = len(personas) > 1

        # Update user interaction timestamp
        self.memory_matrix.update_user_interaction(user_id)

        # Get user preferences (including memory visibility and lives preferences)
        user_preferences = self.user_preferences.get_preferences(user_id)

        # Get or create active life for this user+persona (if roleplay + lives enabled)
        life_id = None
        if (
            "roleplay" in self.features
            and persona
            and user_preferences.get("lives_enabled", True)
        ):
            roleplay_feature = cast(RoleplayFeature, self.features["roleplay"])
            if roleplay_feature.lives_engine:
                life_id = roleplay_feature.lives_engine.ensure_default_life(
                    user_id, persona.persona_id
                )

        # Use user's default memory visibility if not specified
        if memory_visibility is None:
            memory_visibility = user_preferences.get(
                "default_memory_visibility", "ISOLATED"
            )

        # Create context-specific tool registry with user_id and persona_id
        tool_registry = None
        if self.base_tool_registry:
            roleplay_feature = cast(
                Optional[RoleplayFeature], self.features.get("roleplay")
            )

            # Collect feature tools (e.g., roleplay tools)
            feature_tools = []
            if roleplay_feature:
                from core.features.roleplay.tools import ROLEPLAY_TOOLS

                feature_tools.extend(ROLEPLAY_TOOLS)

            tool_registry = ToolRegistry(
                graph_memory=self.graph_memory,
                limbic_engine=roleplay_feature.limbic_engine
                if roleplay_feature
                else None,
                digital_pharmacy=roleplay_feature.digital_pharmacy
                if roleplay_feature
                else None,
                current_user_id=user_id,
                current_persona_id=persona.persona_id if persona else None,
                llm_provider=self.provider,
                feature_tools=feature_tools if feature_tools else None,
            )

        # If vision description is provided, prepend it to the message
        full_message = message
        if vision_description:
            vision_injection = f"[System: The user just uploaded an image showing: {vision_description}]\n\n{message}"
            full_message = vision_injection

        # Save user message to memory (with vision description if present)
        self._save_message_to_memory(
            user_id=user_id,
            persona_id=persona.persona_id if persona else None,
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
                persona_id=persona.persona_id if persona else None,
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
            image_data=image_data,
        )

        if not final_response:
            return None, []

        # Save final assistant response to memory
        save_message("assistant", final_response)

        # Note: AI response already logged by message_processor via log_brain_response()
        # Keeping this would create duplicate console output
        # logger.log_ai_message(persona.persona_id, final_response)

        # Retrieve any generated images from the tool registry
        generated_images = self.message_processor.get_pending_images(tool_registry)

        return final_response, generated_images

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
            "total": len(all_memories),
            "global": global_count,
            "isolated": isolated_count,
        }

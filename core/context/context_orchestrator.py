"""
Context Orchestrator - Main coordinator for conversation context assembly.

This module orchestrates the complete conversation context building process,
coordinating between PromptBuilder, MemoryAssembler, and LimbicInjector.

Part of the Hybrid Memory Architecture split from conversation_builder.py.
Created during RDSSC Phase 1.
"""

from typing import List, Dict, Optional

from core.persona_loader import PersonaCartridge
from core.context.prompt_builder import PromptBuilder
from core.context.memory_assembler import MemoryAssembler
from core.context.limbic_injector import LimbicInjector
from database.memory_matrix import MemoryMatrix
from database.graph_memory import GraphMemory
from database.limbic_engine import LimbicEngine
from database.limbic_modifiers import DigitalPharmacy
from database.metacognition_engine import MetacognitionEngine
from database.mode_manager import ModeManager
from database.user_masks import UserMaskManager
from database.scenario_engine import ScenarioEngine
from core.tool_registry import ToolRegistry


class ConversationContextBuilder:
    """
    Builds conversation context using the Hybrid Memory Architecture.

    MEMORY STRUCTURE (in order):
    1. System Prompt (persona + rules of engagement + tool definitions)
    2. Limbic State Context (INHALE - first-person somatic emotional state)
    3. Substance Modifier (Digital Pharmacy - active substance effects)
    4. Previous Internal Thought (Metacognition continuity)
    5. Knowledge Graph Context (relevant facts extracted by keywords)
    6. Long-Term Semantic Memory (from ChromaDB - semantically relevant past conversations)
    7. Short-Term Chronological Memory (last N messages - immediate conversation flow)
    """

    def __init__(
        self,
        memory_matrix: MemoryMatrix,
        universal_rules: List[str],
        short_term_limit: int,
        semantic_recall_limit: int,
        graph_memory: Optional[GraphMemory] = None,
        limbic_engine: Optional[LimbicEngine] = None,
        digital_pharmacy: Optional[DigitalPharmacy] = None,
        metacognition_engine: Optional[MetacognitionEngine] = None,
        tool_registry: Optional[ToolRegistry] = None,
        mode_manager: Optional[ModeManager] = None,
        user_mask_manager: Optional[UserMaskManager] = None,
        scenario_engine: Optional[ScenarioEngine] = None,
    ):
        """
        Initialize the conversation context builder.

        Args:
            memory_matrix: Memory storage system
            universal_rules: Global behavioral rules for all personas
            short_term_limit: Number of recent messages for immediate context
            semantic_recall_limit: Number of semantic memories to recall
            graph_memory: Optional knowledge graph memory system
            limbic_engine: Optional limbic (emotional) system
            digital_pharmacy: Optional substance-based limbic modifier
            metacognition_engine: Optional internal thought tracking system
            tool_registry: Optional tool registry for function calling
            mode_manager: Optional mode override manager
            user_mask_manager: Optional user mask (persona) system
            scenario_engine: Optional scenario/world tree system
        """
        self.mode_manager = mode_manager

        # Initialize sub-components
        self.prompt_builder = PromptBuilder(
            universal_rules=universal_rules,
            tool_registry=tool_registry,
            user_mask_manager=user_mask_manager,
            scenario_engine=scenario_engine,
            metacognition_engine=metacognition_engine,
        )

        self.memory_assembler = MemoryAssembler(
            memory_matrix=memory_matrix,
            short_term_limit=short_term_limit,
            semantic_recall_limit=semantic_recall_limit,
            graph_memory=graph_memory,
        )

        self.limbic_injector = LimbicInjector(
            limbic_engine=limbic_engine,
            digital_pharmacy=digital_pharmacy,
            metacognition_engine=metacognition_engine,
            user_mask_manager=user_mask_manager,
        )

    def build(
        self,
        user_id: str,
        persona: PersonaCartridge,
        current_message: Optional[str] = None,
        life_id: Optional[str] = None,
        user_preferences: Optional[Dict[str, bool]] = None,
        ensemble_personas: Optional[List[PersonaCartridge]] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the complete conversation context for LLM injection.

        Args:
            user_id: User identifier
            persona: Primary active persona (for backwards compatibility)
            current_message: Optional current user message for semantic search
            life_id: Optional timeline/session ID for memory scoping
            user_preferences: Optional user preference flags
            ensemble_personas: Optional list of ALL active personas (Ensemble Mode)

        Returns:
            List of messages in OpenAI chat format
        """
        # Determine if we're in Ensemble Mode
        personas = ensemble_personas if ensemble_personas else [persona]
        is_ensemble = len(personas) > 1

        # Check for mode overrides
        mode_override = None
        if self.mode_manager:
            mode_override = self.mode_manager.get_mode_override(user_id)

        # Default preferences if not provided
        if user_preferences is None:
            user_preferences = {
                "limbic_enabled": True,
                "metacognition_enabled": True,
            }

        # Apply mode overrides to preferences
        if mode_override:
            if mode_override.disable_limbic:
                user_preferences["limbic_enabled"] = False
            if mode_override.disable_metacognition:
                user_preferences["metacognition_enabled"] = False

        messages = []

        # 1. System Prompt (may be overridden by mode)
        if (
            mode_override
            and mode_override.bypass_persona
            and mode_override.system_prompt_override
        ):
            # OOC mode: Use assistant prompt instead of persona (complete bypass)
            messages.append(
                {
                    "role": "system",
                    "content": mode_override.system_prompt_override,
                }
            )
        else:
            # Normal mode or HENTAI mode: Use persona system prompt
            if is_ensemble:
                system_prompt = self.prompt_builder.build_ensemble_system_prompt(
                    personas, user_preferences, user_id
                )
            else:
                system_prompt = self.prompt_builder.build_system_prompt(
                    persona, user_preferences, user_id
                )

            # HENTAI mode: Append behavioral override at the end (does NOT bypass persona)
            if (
                mode_override
                and not mode_override.bypass_persona
                and mode_override.system_prompt_override
            ):
                system_prompt += "\n\n" + mode_override.system_prompt_override

            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        # 2. Limbic State Context (INHALE phase) - check user preference and mode override
        # In ensemble mode, use the first persona's limbic state
        # Skip for narrator personas (they don't have emotions)
        if (
            user_preferences.get("limbic_enabled", True)
            and not (mode_override and mode_override.disable_limbic)
            and not personas[0].is_narrator
        ):
            limbic_context = self.limbic_injector.build_limbic_context(
                user_id, personas[0]
            )
            if limbic_context:
                messages.append({"role": "system", "content": limbic_context})

        # 3. Substance Modifier (Digital Pharmacy) - requires limbic, disabled in OOC
        # Skip for narrator personas
        if (
            user_preferences.get("limbic_enabled", True)
            and not (mode_override and mode_override.disable_limbic)
            and not personas[0].is_narrator
        ):
            substance_modifier = self.limbic_injector.build_substance_modifier(
                user_id, personas[0].persona_id
            )
            if substance_modifier:
                messages.append({"role": "system", "content": substance_modifier})

        # 4. Previous Internal Thought (Metacognition continuity) - check user preference and mode override
        if user_preferences.get("metacognition_enabled", True) and not (
            mode_override and mode_override.disable_metacognition
        ):
            thought_context = self.limbic_injector.build_thought_context(
                user_id, persona.persona_id
            )
            if thought_context:
                messages.append({"role": "system", "content": thought_context})

        # 5. Knowledge Graph Context (Automated Discretion Engine filtering)
        if current_message:
            kg_context = self.memory_assembler.build_knowledge_graph_context(
                current_message, user_id, persona.persona_id, mode_override
            )
            if kg_context:
                messages.append({"role": "system", "content": kg_context})

        # 6. Long-Term Semantic Memory
        if current_message:
            semantic_context = self.memory_assembler.build_semantic_memory_context(
                user_id, persona.persona_id, current_message, life_id, mode_override
            )
            if semantic_context:
                messages.append({"role": "system", "content": semantic_context})

        # 7. Short-Term Chronological Memory
        short_term_messages = self.memory_assembler.build_short_term_memory(
            user_id, persona.persona_id, life_id, mode_override
        )
        messages.extend(short_term_messages)

        return messages

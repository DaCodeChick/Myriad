"""
ConversationContextBuilder - Builds conversation context for LLM injection.

This module handles the complex task of assembling conversation context using
the Hybrid Memory Architecture, including system prompts, limbic state, knowledge
graph, semantic memories, and short-term chronological memories.

Extracted from AgentCore as part of RDSSC Phase 3.
"""

from typing import List, Dict, Optional

from core.persona_loader import PersonaCartridge
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
        self.memory_matrix = memory_matrix
        self.universal_rules = universal_rules
        self.short_term_limit = short_term_limit
        self.semantic_recall_limit = semantic_recall_limit
        self.graph_memory = graph_memory
        self.limbic_engine = limbic_engine
        self.digital_pharmacy = digital_pharmacy
        self.metacognition_engine = metacognition_engine
        self.tool_registry = tool_registry
        self.mode_manager = mode_manager
        self.user_mask_manager = user_mask_manager
        self.scenario_engine = scenario_engine

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
                system_prompt = self._build_ensemble_system_prompt(
                    personas, user_preferences, user_id
                )
            else:
                system_prompt = self._build_system_prompt(
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
        if user_preferences.get("limbic_enabled", True) and not (
            mode_override and mode_override.disable_limbic
        ):
            limbic_context = self._build_limbic_context(user_id, personas[0])
            if limbic_context:
                messages.append({"role": "system", "content": limbic_context})

        # 3. Substance Modifier (Digital Pharmacy) - requires limbic, disabled in OOC
        if user_preferences.get("limbic_enabled", True) and not (
            mode_override and mode_override.disable_limbic
        ):
            substance_modifier = self._build_substance_modifier(
                user_id, personas[0].persona_id
            )
            if substance_modifier:
                messages.append({"role": "system", "content": substance_modifier})

        # 4. Previous Internal Thought (Metacognition continuity) - check user preference and mode override
        if user_preferences.get("metacognition_enabled", True) and not (
            mode_override and mode_override.disable_metacognition
        ):
            thought_context = self._build_thought_context(user_id, persona.persona_id)
            if thought_context:
                messages.append({"role": "system", "content": thought_context})

        # 5. Knowledge Graph Context (Automated Discretion Engine filtering)
        if current_message:
            kg_context = self._build_knowledge_graph_context(
                current_message, user_id, persona.persona_id, mode_override
            )
            if kg_context:
                messages.append({"role": "system", "content": kg_context})

        # 6. Long-Term Semantic Memory
        if current_message:
            semantic_context = self._build_semantic_memory_context(
                user_id, persona.persona_id, current_message, life_id, mode_override
            )
            if semantic_context:
                messages.append({"role": "system", "content": semantic_context})

        # 7. Short-Term Chronological Memory
        short_term_messages = self._build_short_term_memory(
            user_id, persona.persona_id, life_id, mode_override
        )
        messages.extend(short_term_messages)

        return messages

    def _build_system_prompt(
        self, persona: PersonaCartridge, user_preferences: Dict[str, bool], user_id: str
    ) -> str:
        """
        Build the complete system prompt including universal rules, persona identity,
        background/lore, user mask, tool definitions, and metacognition instructions.

        Applies relationship overrides if the user has an active mask that matches
        a relationship in the persona's relationships array.
        """
        # Check for relationship overrides based on active user mask
        active_relationship = None
        active_mask_name = None
        if self.user_mask_manager:
            user_mask = self.user_mask_manager.get_active_mask(user_id)
            if user_mask:
                active_mask_name = user_mask.name
                # Check if persona has a relationship override for this mask's persona_id
                active_relationship = persona.get_relationship_override(
                    user_mask.persona_id
                )

        # Apply relationship overrides to create a modified persona view
        effective_personality_traits = persona.personality_traits
        effective_rules = persona.rules_of_engagement

        if active_relationship:
            if active_relationship.personality_traits_override:
                effective_personality_traits = (
                    active_relationship.personality_traits_override
                )
            if active_relationship.rules_of_engagement_override:
                effective_rules = active_relationship.rules_of_engagement_override

        # Start with [CORE SYSTEM DIRECTIVES]
        content = "# [CORE SYSTEM DIRECTIVES]\n"
        content += "The following directives apply universally to all interactions:\n\n"
        content += "\n".join(f"- {rule}" for rule in self.universal_rules)

        # Add persona's core identity and system prompt
        content += f"\n\n# [CHARACTER IDENTITY]\n{persona.system_prompt}"

        # Inject relationship context if override is active
        if active_relationship:
            content += (
                f"\n\n# [RELATIONSHIP CONTEXT]\n{active_relationship.description}"
            )

        # Inject AI physical appearance if defined (cached from vision model)
        if persona.cached_appearance:
            content += f"\n\n# [AI PHYSICAL APPEARANCE]\n{persona.cached_appearance}"

        # Inject background/lore if defined (deep historical context)
        if persona.background:
            content += f"\n\n# [BACKGROUND / LORE]\n{persona.background}"

        # Inject User Mask (if user is wearing a persona)
        if self.user_mask_manager:
            user_mask = self.user_mask_manager.get_active_mask(user_id)
            if user_mask:
                content += "\n\n# [ACTIVE INTERLOCUTOR IDENTITY]\n"
                content += "The user is currently embodying the following persona:\n\n"
                content += f"**Name:** {user_mask.name}\n"
                content += f"**Identity:** {user_mask.system_prompt}\n"
                if user_mask.background:
                    content += f"**Lore/Background:** {user_mask.background}\n"

                # Inject user's physical appearance if cached
                if user_mask.cached_appearance:
                    content += (
                        f"**Physical Appearance:** {user_mask.cached_appearance}\n"
                    )

                content += (
                    "\n**DIRECTIVE:** You must respond to the user as this character, "
                    "respecting all established lore and relationship dynamics between your persona and theirs. "
                    "Address them by their character name when appropriate and maintain consistency with their backstory."
                )

        # Inject Scenario Hierarchy (Environmental Context / World Tree)
        if self.scenario_engine:
            active_scenario = self.scenario_engine.get_active_scenario(user_id)
            if active_scenario:
                # Get the full hierarchy from macro to micro using recursive CTE
                scenario_hierarchy = self.scenario_engine.get_scenario_hierarchy(
                    active_scenario.name
                )

                if scenario_hierarchy:
                    content += "\n\n# [ENVIRONMENTAL CONTEXT]\n"
                    content += (
                        "You are currently existing within the following nested environment "
                        "(from macro world state to immediate location):\n\n"
                    )

                    # Build the hierarchy display from macro (root) to micro (active)
                    for i, scenario in enumerate(scenario_hierarchy):
                        indent = "  " * i
                        if i == 0:
                            level_label = "World State"
                        elif i == len(scenario_hierarchy) - 1:
                            level_label = "Immediate Location"
                        else:
                            level_label = "Macro Location" if i == 1 else "Location"

                        content += (
                            f"{indent}• **{level_label} ({scenario.name})**: "
                            f"{scenario.description}\n"
                        )

                    content += (
                        "\n**DIRECTIVE:** You are currently existing within this nested environment. "
                        "Obey the physics, rules, and atmosphere of these locations. "
                        "Your responses must be consistent with the environmental constraints and context. "
                        "If actions or events contradict the established setting, you should note the inconsistency."
                    )

        # Add persona-specific behavioral rules if they exist (with relationship overrides applied)
        if effective_rules:
            content += "\n\n# [PERSONA-SPECIFIC BEHAVIOR]\n"
            content += (
                "Additional behavioral guidelines specific to this character:\n\n"
            )
            content += "\n".join(f"- {rule}" for rule in effective_rules)

        # Inject tool definitions if available
        if self.tool_registry:
            tool_definitions = self.tool_registry.get_tool_definitions_text()
            if tool_definitions:
                content += tool_definitions

                # Add importance scoring guidelines for memory tools
                content += (
                    "\n\n## MEMORY IMPORTANCE SCORING:\n"
                    "When storing information using memory tools (like add_knowledge), use the importance_score parameter (1-10) to indicate how critical the information is:\n\n"
                    "**1-3: Trivial/Casual**\n"
                    "- Small talk preferences (favorite color, weather opinions)\n"
                    "- Casual interests or passing remarks\n"
                    "- Easily changeable preferences\n\n"
                    "**4-6: Standard Facts** [DEFAULT]\n"
                    "- Work, occupation, or hobbies\n"
                    "- General interests and activities\n"
                    "- Normal biographical information\n\n"
                    "**7-9: Significant Information**\n"
                    "- Personal values and core beliefs\n"
                    "- Important boundaries or preferences\n"
                    "- Major life events or relationships\n"
                    "- Strong emotional attachments or aversions\n\n"
                    "**10: CORE ANCHORS (Critical)**\n"
                    "- Severe trauma or PTSD triggers\n"
                    "- Hard limits and absolute boundaries\n"
                    "- Life-threatening allergies or medical conditions\n"
                    "- Core identity elements that must never be violated\n\n"
                    "Score information accurately based on its impact on the user's wellbeing and your future interactions. "
                    "High-importance memories (8-10) will be surfaced more frequently in retrieval, even if semantically distant from the current topic."
                )

        # Inject metacognition instruction if enabled (check both global and user preference)
        if self.metacognition_engine and user_preferences.get(
            "metacognition_enabled", True
        ):
            content += (
                "\n\n## METACOGNITION PROTOCOL:\n"
                "Before you reply, you MUST wrap your internal monologue and planning in <thought> and </thought> tags. "
                "This space is private. Use it to plan your manipulation, evaluate the user, or process your Limbic state before taking action.\n"
                "Example:\n"
                "<thought>\n"
                "The user seems anxious. My serotonin is elevated, making me empathetic. I should offer reassurance while subtly steering the conversation toward their deeper fears.\n"
                "</thought>\n"
                "Then provide your actual response after the thought block."
            )

        return content

    def _build_ensemble_system_prompt(
        self,
        personas: List[PersonaCartridge],
        user_preferences: Dict[str, bool],
        user_id: str,
    ) -> str:
        """
        Build system prompt for ENSEMBLE MODE (multiple active AI personas).

        This injects a master Dungeon Master directive and loops through all active personas,
        including their full personality blocks and relationship overrides for each user mask.
        """
        # Get all active user masks
        active_masks = []
        if self.user_mask_manager:
            active_masks = self.user_mask_manager.get_active_masks(user_id)

        # Start with [CORE SYSTEM DIRECTIVES]
        content = "# [CORE SYSTEM DIRECTIVES]\n"
        content += "The following directives apply universally to all interactions:\n\n"
        content += "\n".join(f"- {rule}" for rule in self.universal_rules)

        # ENSEMBLE MODE MASTER DIRECTIVE
        content += "\n\n# [🎭 ENSEMBLE MODE ACTIVE]\n"
        content += (
            "**YOU ARE THE DUNGEON MASTER/NARRATOR FOR THIS SCENE.**\n\n"
            f"You are actively puppeteering **{len(personas)} characters** simultaneously. "
            "Your task is to dynamically manage their dialogue and actions, clearly indicating who is speaking or acting at any given moment. "
            "Each character maintains their unique voice, personality, and perspective.\n\n"
            "**Format for multi-character responses:**\n"
            "- Use character names in bold before their dialogue/actions: **[Character Name]:** dialogue/action\n"
            "- Switch perspectives fluidly but clearly\n"
            "- Allow characters to interact with each other naturally\n"
            "- Maintain consistency with each character's personality and relationships\n"
        )

        # Inject each AI Persona
        content += "\n\n# [ACTIVE AI CHARACTERS]\n"
        content += f"You are currently controlling the following {len(personas)} character(s):\n\n"

        for i, persona in enumerate(personas, 1):
            content += f"\n## CHARACTER {i}: {persona.name}\n\n"
            content += f"**Core Identity:**\n{persona.system_prompt}\n\n"

            # Inject physical appearance if cached
            if persona.cached_appearance:
                content += f"**Physical Appearance:**\n{persona.cached_appearance}\n\n"

            # Inject background/lore
            if persona.background:
                content += f"**Background/Lore:**\n{persona.background}\n\n"

            # Inject personality traits
            if persona.personality_traits:
                content += f"**Personality Traits:**\n{persona.personality_traits}\n\n"

            # Inject rules of engagement
            if persona.rules_of_engagement:
                content += (
                    f"**Rules of Engagement:**\n{persona.rules_of_engagement}\n\n"
                )

            # RELATIONSHIP ENGINE: Check this persona against ALL user masks
            if active_masks:
                content += f"**{persona.name}'s Relationships:**\n"
                for mask in active_masks:
                    relationship = persona.get_relationship_override(mask.persona_id)
                    if relationship:
                        content += f"\n- **Relationship with {mask.name}:** {relationship.description}\n"
                        if relationship.personality_traits_override:
                            content += f"  - *Personality when interacting with {mask.name}:* {relationship.personality_traits_override}\n"
                        if relationship.rules_of_engagement_override:
                            content += f"  - *Behavioral rules with {mask.name}:* {relationship.rules_of_engagement_override}\n"
                        if relationship.limbic_baseline_override:
                            content += f"  - *Emotional baseline with {mask.name}:* {relationship.limbic_baseline_override}\n"
                    else:
                        content += f"\n- **Relationship with {mask.name}:** No special relationship defined (default interaction)\n"
                content += "\n"

        # Inject User Masks Ensemble
        if active_masks:
            content += "\n\n# [👥 USER ENSEMBLE]\n"
            content += f"The user is actively embodying **{len(active_masks)} character(s)** in this scene:\n\n"

            for i, mask in enumerate(active_masks, 1):
                content += f"\n## USER CHARACTER {i}: {mask.name}\n\n"
                content += f"**Identity:** {mask.system_prompt}\n"

                if mask.background:
                    content += f"**Lore/Background:** {mask.background}\n"

                if mask.cached_appearance:
                    content += f"**Physical Appearance:** {mask.cached_appearance}\n"

                content += "\n"

            content += (
                "\n**DIRECTIVE:** You must respond to the user as their characters, "
                "respecting all established lore and relationship dynamics. "
                "Your AI characters should interact with each user character according to their defined relationships. "
                "When the user speaks, they may indicate which character is speaking, or you should infer from context."
            )

        # Inject Scenario Hierarchy (Environmental Context / World Tree)
        if self.scenario_engine:
            active_scenario = self.scenario_engine.get_active_scenario(user_id)
            if active_scenario:
                scenario_hierarchy = self.scenario_engine.get_scenario_hierarchy(
                    active_scenario.name
                )

                if scenario_hierarchy:
                    content += "\n\n# [ENVIRONMENTAL CONTEXT]\n"
                    content += (
                        "All characters are existing within the following nested environment "
                        "(from macro world state to immediate location):\n\n"
                    )

                    for i, scenario in enumerate(scenario_hierarchy):
                        indent = "  " * i
                        if i == 0:
                            level_label = "World State"
                        elif i == len(scenario_hierarchy) - 1:
                            level_label = "Current Location"
                        else:
                            level_label = "Macro Location"

                        content += f"{indent}**{level_label}:** {scenario.name}\n"
                        content += f"{indent}*Description:* {scenario.description}\n"

                        # Inject cached appearance for scenario if available
                        if scenario.cached_appearance:
                            content += f"{indent}*Visual Description:* {scenario.cached_appearance}\n"

                        content += "\n"

        # Tool definitions
        if self.tool_registry:
            tool_definitions = self.tool_registry.get_tool_definitions_text()
            if tool_definitions:
                content += f"\n\n# [AVAILABLE TOOLS]\n{tool_definitions}"

        # Memory importance scoring
        if user_preferences.get("memory_importance_enabled", True):
            content += (
                "\n\n## MEMORY IMPORTANCE SCORING:\n"
                "When the user shares information, evaluate its long-term significance and assign an importance score (1-10).\n\n"
                "**1-3: Ephemeral/Trivial**\n"
                "- Weather, time, or temporary states\n"
                "- Casual greetings or pleasantries\n"
                "- Easily changeable preferences\n\n"
                "**4-6: Standard Facts** [DEFAULT]\n"
                "- Work, occupation, or hobbies\n"
                "- General interests and activities\n"
                "- Normal biographical information\n\n"
                "**7-9: Significant Information**\n"
                "- Personal values and core beliefs\n"
                "- Important boundaries or preferences\n"
                "- Major life events or relationships\n"
                "- Strong emotional attachments or aversions\n\n"
                "**10: CORE ANCHORS (Critical)**\n"
                "- Severe trauma or PTSD triggers\n"
                "- Hard limits and absolute boundaries\n"
                "- Life-threatening allergies or medical conditions\n"
                "- Core identity elements that must never be violated\n\n"
                "Score information accurately based on its impact on the user's wellbeing and your future interactions."
            )

        # Metacognition instruction
        if self.metacognition_engine and user_preferences.get(
            "metacognition_enabled", True
        ):
            content += (
                "\n\n## METACOGNITION PROTOCOL:\n"
                "Before you reply, you MUST wrap your internal monologue and planning in <thought> and </thought> tags. "
                "This space is private. Use it to plan character actions, evaluate relationships, or process emotional states.\n"
                "Example:\n"
                "<thought>\n"
                "Magus would be conflicted seeing Schala here. His protective instinct wars with his pride. "
                "I'll have him respond tersely at first, then soften when he sees she's in distress.\n"
                "</thought>\n"
                "Then provide your actual response with character names clearly labeled."
            )

        return content

    def _build_limbic_context(
        self, user_id: str, persona: "PersonaCartridge"
    ) -> Optional[str]:
        """
        Build limbic state context (emotional state as first-person somatic context).

        Applies relationship limbic baseline overrides if the user has an active mask
        that matches a relationship in the persona's relationships array.
        """
        if not self.limbic_engine:
            return None

        # Check for relationship limbic baseline override
        effective_baseline = persona.limbic_baseline
        if self.user_mask_manager:
            user_mask = self.user_mask_manager.get_active_mask(user_id)
            if user_mask:
                active_relationship = persona.get_relationship_override(
                    user_mask.persona_id
                )
                if active_relationship and active_relationship.limbic_baseline_override:
                    # Merge relationship override with base baseline
                    effective_baseline = (
                        persona.limbic_baseline.copy()
                        if persona.limbic_baseline
                        else {}
                    )
                    effective_baseline.update(
                        active_relationship.limbic_baseline_override
                    )

        return self.limbic_engine.get_limbic_context(
            user_id=user_id,
            persona_id=persona.persona_id,
            persona_baseline=effective_baseline,
        )

    def _build_substance_modifier(self, user_id: str, persona_id: str) -> Optional[str]:
        """Build substance prompt modifier (Digital Pharmacy effects)."""
        if not self.digital_pharmacy:
            return None

        return self.digital_pharmacy.get_substance_prompt_modifier(
            user_id=user_id, persona_id=persona_id
        )

    def _build_thought_context(self, user_id: str, persona_id: str) -> Optional[str]:
        """Build previous thought context for metacognition continuity."""
        if not self.metacognition_engine:
            return None

        previous_thought = self.metacognition_engine.get_previous_thought(
            user_id=user_id, persona_id=persona_id
        )

        if previous_thought:
            return f"[Previous Internal Thought: {previous_thought}]"

        return None

    def _build_knowledge_graph_context(
        self,
        current_message: str,
        user_id: str,
        persona_id: str,
        mode_override=None,
    ) -> Optional[str]:
        """
        Build knowledge graph context from current message keywords.

        Automated Discretion Engine: Filters knowledge to show only:
        - user_id == current_user AND (persona_id == current_persona OR scope == 'global')

        OOC Mode Override: Access ALL knowledge across all users/personas/lives.

        Args:
            current_message: Current user message for keyword extraction
            user_id: User ID for filtering
            persona_id: Current persona ID for filtering
            mode_override: Optional mode override configuration

        Returns:
            Formatted knowledge graph context or None
        """
        if not self.graph_memory:
            return None

        # In OOC mode, bypass filtering for global access
        if mode_override and mode_override.global_memory_access:
            return self.graph_memory.get_knowledge_context(
                current_message, user_id=None, current_persona=None
            )

        return self.graph_memory.get_knowledge_context(
            current_message, user_id=user_id, current_persona=persona_id
        )

    def _build_semantic_memory_context(
        self,
        user_id: str,
        persona_id: str,
        query: str,
        life_id: Optional[str] = None,
        mode_override=None,
    ) -> Optional[str]:
        """
        Build long-term semantic memory context from ChromaDB.

        OOC Mode Override: Access ALL memories across all users/personas/lives.
        """
        if not self.memory_matrix.vector_memory_enabled:
            return None

        # In OOC mode, bypass filtering for global access
        if mode_override and mode_override.global_memory_access:
            semantic_memories = self.memory_matrix.search_semantic_memories(
                user_id=None,  # No user filtering in OOC
                current_persona=None,  # No persona filtering in OOC
                query=query,
                limit=self.semantic_recall_limit,
                life_id=None,  # No life filtering in OOC
            )
        else:
            semantic_memories = self.memory_matrix.search_semantic_memories(
                user_id=user_id,
                current_persona=persona_id,
                query=query,
                limit=self.semantic_recall_limit,
                life_id=life_id,
            )

        if not semantic_memories:
            return None

        # Format semantic memories
        if mode_override and mode_override.global_memory_access:
            content = "[OOC MODE - Global Memory Access: Memories from ALL personas and timelines]\n\n"
        else:
            content = "[Recalled Long-Term Context: Semantically relevant memories from past conversations]\n\n"

        for i, memory in enumerate(semantic_memories, 1):
            metadata = memory.get("metadata", {})
            memory_content = memory.get("content", "")
            role = metadata.get("role", "unknown")
            timestamp = metadata.get("timestamp", "unknown")

            # In OOC mode, show extra metadata
            if mode_override and mode_override.global_memory_access:
                origin_persona = metadata.get("origin_persona", "unknown")
                user_id_meta = metadata.get("user_id", "unknown")
                content += f"{i}. [User: {user_id_meta} | Persona: {origin_persona} | {role.upper()} - {timestamp}]: {memory_content}\n\n"
            else:
                content += f"{i}. [{role.upper()} - {timestamp}]: {memory_content}\n\n"

        content += "[End of Recalled Context]\n"

        return content

    def _build_short_term_memory(
        self,
        user_id: str,
        persona_id: str,
        life_id: Optional[str] = None,
        mode_override=None,
    ) -> List[Dict[str, str]]:
        """
        Build short-term chronological memory (last N messages).

        OOC Mode Override: Access ALL recent messages across all personas/lives.
        """
        # In OOC mode, bypass filtering for global access
        if mode_override and mode_override.global_memory_access:
            short_term_memories = self.memory_matrix.get_context_memories(
                user_id=None,  # No user filtering in OOC
                current_persona=None,  # No persona filtering in OOC
                limit=self.short_term_limit,
                life_id=None,  # No life filtering in OOC
            )
        else:
            short_term_memories = self.memory_matrix.get_context_memories(
                user_id=user_id,
                current_persona=persona_id,
                limit=self.short_term_limit,
                life_id=life_id,
            )

        # Convert to OpenAI format
        return [
            {"role": memory["role"], "content": memory["content"]}
            for memory in short_term_memories
        ]

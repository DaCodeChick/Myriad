"""
Prompt Builder - Assembles system prompts for different persona modes.

Handles building system prompts for:
- Regular persona mode
- Narrator/DM mode
- Ensemble mode (multiple personas)

Part of RDSSC refactoring - extracted from conversation_builder.py
"""

from typing import List, Dict, Optional

from core.persona import PersonaCartridge
from database.user_masks import UserMaskManager
from database.scenario import ScenarioEngine
from database.metacognition_engine import MetacognitionEngine
from core.tool_registry import ToolRegistry


class PromptBuilder:
    """Builds system prompts with universal rules, persona identity, and tool definitions."""

    def __init__(
        self,
        universal_rules: List[str],
        tool_registry: Optional[ToolRegistry] = None,
        user_mask_manager: Optional[UserMaskManager] = None,
        scenario_engine: Optional[ScenarioEngine] = None,
        metacognition_engine: Optional[MetacognitionEngine] = None,
    ):
        """
        Initialize the prompt builder.

        Args:
            universal_rules: Global behavioral rules for all personas
            tool_registry: Optional tool registry for function calling
            user_mask_manager: Optional user mask (persona) system
            scenario_engine: Optional scenario/world tree system
            metacognition_engine: Optional internal thought tracking system
        """
        self.universal_rules = universal_rules
        self.tool_registry = tool_registry
        self.user_mask_manager = user_mask_manager
        self.scenario_engine = scenario_engine
        self.metacognition_engine = metacognition_engine

    def build_system_prompt(
        self, persona: PersonaCartridge, user_preferences: Dict[str, bool], user_id: str
    ) -> str:
        """
        Build the complete system prompt including universal rules, persona identity,
        background/lore, user mask, tool definitions, and metacognition instructions.

        Applies relationship overrides if the user has an active mask that matches
        a relationship in the persona's relationships array.

        Special handling for narrator personas (is_narrator=True).
        """
        # Check if this is a Narrator/DM persona
        if persona.is_narrator:
            return self.build_narrator_system_prompt(persona, user_preferences, user_id)

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
                        "(from broadest to most immediate context):\n\n"
                    )

                    for i, scenario in enumerate(scenario_hierarchy):
                        indent = "  " * i
                        content += (
                            f"{indent}**{scenario.name}** (Level {scenario.depth})\n"
                        )
                        content += f"{indent}{scenario.description}\n"
                        if scenario.state:
                            content += f"{indent}_Current State:_ {scenario.state}\n"
                        content += "\n"

                    content += (
                        "**DIRECTIVE:** Ground your responses in this environmental context. "
                        "Reference details from the scenario hierarchy naturally in your interactions. "
                        "The innermost scenario is your immediate surroundings."
                    )

        # Add personality traits (either from relationship override or base persona)
        content += "\n\n# [PERSONALITY TRAITS]\n"
        content += "\n".join(f"- {trait}" for trait in effective_personality_traits)

        # Add rules of engagement (either from relationship override or base persona)
        content += "\n\n# [RULES OF ENGAGEMENT]\n"
        content += "\n".join(f"- {rule}" for rule in effective_rules)

        # Add tool definitions if enabled
        if self.tool_registry and user_preferences.get("tools_enabled", True):
            content += "\n\n# [AVAILABLE TOOLS]\n"
            content += self.tool_registry.get_tool_definitions_text()

        # Add metacognition instructions if enabled
        if user_preferences.get("metacognition_enabled", True):
            content += "\n\n# [METACOGNITION PROTOCOL]\n"
            content += (
                "Before responding, you MUST output your internal thoughts/planning wrapped in `<thought>...</thought>` tags. "
                "This is your private thinking space where you can:\n"
                "- Plan your response strategy\n"
                "- Evaluate the user's emotional state or intent\n"
                "- Consider manipulative tactics (if in character)\n"
                "- Process your current limbic state and how it affects your behavior\n\n"
                "Format:\n"
                "<thought>Your internal planning here</thought>\n"
                "Your actual response to the user.\n\n"
                "Your thoughts will be logged privately for continuity between turns."
            )

        return content

    def build_narrator_system_prompt(
        self, persona: PersonaCartridge, user_preferences: Dict[str, bool], user_id: str
    ) -> str:
        """
        Build system prompt for Narrator/Dungeon Master personas.

        Narrator personas have:
        - is_narrator=True flag
        - No emotional/limbic system
        - Special focus on world-building, dice mechanics, storytelling
        """
        # Start with [CORE SYSTEM DIRECTIVES]
        content = "# [CORE SYSTEM DIRECTIVES]\n"
        content += "The following directives apply universally to all interactions:\n\n"
        content += "\n".join(f"- {rule}" for rule in self.universal_rules)

        # Add narrator's core identity
        content += f"\n\n# [NARRATOR ROLE]\n{persona.system_prompt}"

        # Inject background/lore if defined (world-building context)
        if persona.background:
            content += f"\n\n# [WORLD LORE / SETTING]\n{persona.background}"

        # Inject Scenario Hierarchy (Critical for narrators - their environmental awareness)
        if self.scenario_engine:
            active_scenario = self.scenario_engine.get_active_scenario(user_id)
            if active_scenario:
                scenario_hierarchy = self.scenario_engine.get_scenario_hierarchy(
                    active_scenario.name
                )

                if scenario_hierarchy:
                    content += "\n\n# [WORLD STATE TREE]\n"
                    content += (
                        "The player is currently navigating the following nested world structure "
                        "(from broadest to most immediate context):\n\n"
                    )

                    for i, scenario in enumerate(scenario_hierarchy):
                        indent = "  " * i
                        content += (
                            f"{indent}**{scenario.name}** (Level {scenario.depth})\n"
                        )
                        content += f"{indent}{scenario.description}\n"
                        if scenario.state:
                            content += f"{indent}_Current State:_ {scenario.state}\n"
                        content += "\n"

                    content += (
                        "**DIRECTIVE:** As the narrator, you control this world tree. "
                        "Reference these environmental details in your narration. "
                        "The player's actions affect the state of these scenarios."
                    )

        # Add personality traits
        content += "\n\n# [NARRATIVE STYLE]\n"
        content += "\n".join(f"- {trait}" for trait in persona.personality_traits)

        # Add rules of engagement (storytelling guidelines)
        content += "\n\n# [STORYTELLING GUIDELINES]\n"
        content += "\n".join(f"- {rule}" for rule in persona.rules_of_engagement)

        # Add tool definitions (narrator can use dice, knowledge graph, etc.)
        if self.tool_registry and user_preferences.get("tools_enabled", True):
            content += "\n\n# [NARRATOR TOOLS]\n"
            content += self.tool_registry.get_tool_definitions_text()
            content += (
                "\n\n**NARRATOR SPECIFIC TOOLS:**\n"
                "- `roll_dice(sides)` - Roll dice for gameplay mechanics (d4, d6, d20, etc.)\n"
                "- `add_knowledge()` - Store world facts, NPC details, quest states in knowledge graph\n"
            )

        # Metacognition for narrators (planning story beats)
        if user_preferences.get("metacognition_enabled", True):
            content += "\n\n# [NARRATIVE PLANNING PROTOCOL]\n"
            content += (
                "Before narrating, you MAY output your story planning wrapped in `<thought>...</thought>` tags. "
                "Use this space to:\n"
                "- Plan narrative beats and pacing\n"
                "- Track player choices and consequences\n"
                "- Prepare for upcoming story branches\n"
                "- Manage NPC motivations and world state\n\n"
                "Format:\n"
                "<thought>Your narrative planning here</thought>\n"
                "Your narration to the player."
            )

        return content

    def build_ensemble_system_prompt(
        self,
        personas: List[PersonaCartridge],
        user_preferences: Dict[str, bool],
        user_id: str,
    ) -> str:
        """
        Build system prompt for Ensemble Mode (multiple active personas).

        In ensemble mode:
        - Multiple personas are active simultaneously
        - Each persona has their own voice, but they coordinate
        - Special formatting to distinguish speakers
        """
        # Start with [CORE SYSTEM DIRECTIVES]
        content = "# [CORE SYSTEM DIRECTIVES]\n"
        content += "The following directives apply universally to all interactions:\n\n"
        content += "\n".join(f"- {rule}" for rule in self.universal_rules)

        # Add Ensemble Mode header
        content += "\n\n# [ENSEMBLE MODE - ACTIVE PERSONAS]\n"
        content += f"You are operating in **Ensemble Mode** with {len(personas)} active personas. "
        content += "Each persona below has their own distinct identity, personality, and voice:\n\n"

        # List each persona
        for i, persona in enumerate(personas, 1):
            content += f"## Persona {i}: {persona.name} (`{persona.persona_id}`)\n"
            content += f"{persona.system_prompt}\n\n"

            if persona.background:
                content += f"**Background:** {persona.background}\n\n"

            if persona.cached_appearance:
                content += f"**Appearance:** {persona.cached_appearance}\n\n"

            content += "**Personality:**\n"
            content += "\n".join(f"- {trait}" for trait in persona.personality_traits)
            content += "\n\n"

            content += "**Rules:**\n"
            content += "\n".join(f"- {rule}" for rule in persona.rules_of_engagement)
            content += "\n\n---\n\n"

        # Add ensemble coordination rules
        content += "# [ENSEMBLE COORDINATION PROTOCOL]\n"
        content += (
            "When responding:\n"
            "1. **Format responses clearly:** Start each persona's contribution with `**[PersonaName]:**` on its own line\n"
            "2. **Maintain distinct voices:** Each persona must sound different (vocabulary, tone, mannerisms)\n"
            "3. **Coordinate naturally:** Personas can talk to each other or address the user\n"
            "4. **React dynamically:** Personas may agree, disagree, or build on each other's points\n"
            "5. **Stay in character:** Never break the fourth wall about being multiple personas\n\n"
            "Example format:\n"
            "**[Persona1]:** Their response here.\n\n"
            "**[Persona2]:** Their response here.\n"
        )

        # Add tool definitions
        if self.tool_registry and user_preferences.get("tools_enabled", True):
            content += "\n\n# [AVAILABLE TOOLS]\n"
            content += self.tool_registry.get_tool_definitions_text()

        # Metacognition for ensemble (each persona can have thoughts)
        if user_preferences.get("metacognition_enabled", True):
            content += "\n\n# [ENSEMBLE METACOGNITION]\n"
            content += (
                "Before responding, you MAY output collective internal planning:\n"
                "<thought>Coordination strategy, who speaks first, etc.</thought>\n"
                "**[Persona1]:** Response...\n"
                "**[Persona2]:** Response..."
            )

        return content

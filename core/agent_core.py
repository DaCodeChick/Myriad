"""
AgentCore - The platform-agnostic intelligence engine for Project Myriad.

This module is the central brain of the system. It:
1. Manages persona switching and state
2. Handles memory injection via the Automated Discretion Engine
3. Communicates with the LLM API
4. Processes messages and generates responses
5. Executes tool calls (function calling)

CRITICAL: This module must NEVER import discord or any platform-specific code.
It operates purely on strings and data structures.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from database.memory_matrix import MemoryMatrix
from database.graph_memory import GraphMemory
from database.limbic_engine import LimbicEngine
from database.limbic_modifiers import DigitalPharmacy
from database.metacognition_engine import MetacognitionEngine
from database.lives_engine import LivesEngine
from database.save_states_engine import SaveStatesEngine
from core.persona_loader import PersonaLoader, PersonaCartridge
from core.tool_registry import ToolRegistry, parse_tool_call, format_tool_response
from core.cadence_degrader import CadenceDegrader


class AgentCore:
    """
    The platform-agnostic AI engine.

    This class is the core intelligence that can be adapted to any frontend
    (Discord, Telegram, CLI, web interface, etc.)
    """

    # ========================
    # UNIVERSAL DIRECTIVES
    # ========================
    # Global formatting and behavior rules that apply to ALL personas.
    # These are injected at the very top of the system prompt as [CORE SYSTEM DIRECTIVES].
    UNIVERSAL_RULES = [
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
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        short_term_limit: int = 10,
        db_path: str = "data/myriad_state.db",
        personas_dir: str = "personas",
        vector_memory_enabled: bool = True,
        semantic_recall_limit: int = 5,
        tools_enabled: bool = True,
        max_tool_iterations: int = 5,
        graph_memory_enabled: bool = True,
        graph_db_path: str = "data/knowledge_graph.db",
        limbic_enabled: bool = True,
        limbic_db_path: str = "data/limbic_state.db",
        digital_pharmacy_enabled: bool = True,
        cadence_degrader_enabled: bool = True,
        metacognition_enabled: bool = True,
        metacognition_db_path: str = "data/metacognition.db",
        show_thoughts_inline: bool = True,
        lives_enabled: bool = True,
    ):
        """
        Initialize the AgentCore.

        Args:
            api_key: OpenAI API key (or compatible API)
            base_url: LLM API base URL (allows pointing to OpenRouter, local, etc.)
            model: Model name to use
            short_term_limit: Number of recent messages for immediate conversation context (default: 10)
            db_path: Path to SQLite database
            personas_dir: Directory containing persona JSON files
            vector_memory_enabled: Enable semantic vector memory (default: True)
            semantic_recall_limit: Number of semantic memories to recall from long-term storage (default: 5)
            tools_enabled: Enable tool use / function calling (default: True)
            max_tool_iterations: Maximum number of tool calls in a single response cycle (default: 5)
            graph_memory_enabled: Enable knowledge graph memory (default: True)
            graph_db_path: Path to knowledge graph SQLite database (default: data/knowledge_graph.db)
            limbic_enabled: Enable limbic system (emotional neurochemistry) (default: True)
            limbic_db_path: Path to limbic state SQLite database (default: data/limbic_state.db)
            digital_pharmacy_enabled: Enable Digital Pharmacy (substance-based limbic overrides) (default: True)
            cadence_degrader_enabled: Enable Cadence Degradation Engine (text post-processing) (default: True)
            metacognition_enabled: Enable Metacognition Engine (internal thought tracking) (default: True)
            metacognition_db_path: Path to metacognition SQLite database (default: data/metacognition.db)
            show_thoughts_inline: Display thoughts inline in responses vs. terminal-only (default: True)
            lives_enabled: Enable Lives & Memories system (timelines and save states) (default: True)
        """
        # LLM Client
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.short_term_limit = short_term_limit
        self.semantic_recall_limit = semantic_recall_limit
        self.tools_enabled = tools_enabled
        self.max_tool_iterations = max_tool_iterations
        self.graph_memory_enabled = graph_memory_enabled
        self.limbic_enabled = limbic_enabled
        self.digital_pharmacy_enabled = digital_pharmacy_enabled
        self.cadence_degrader_enabled = cadence_degrader_enabled
        self.lives_enabled = lives_enabled

        # Core Systems
        self.memory_matrix = MemoryMatrix(
            db_path=db_path, vector_memory_enabled=vector_memory_enabled
        )
        self.persona_loader = PersonaLoader(personas_dir=personas_dir)

        # Knowledge Graph Memory
        self.graph_memory = (
            GraphMemory(db_path=graph_db_path) if graph_memory_enabled else None
        )

        # Limbic System (Emotional Neurochemistry)
        self.limbic_engine = (
            LimbicEngine(db_path=limbic_db_path) if limbic_enabled else None
        )

        # Digital Pharmacy (Substance-Based Limbic Overrides)
        self.digital_pharmacy = (
            DigitalPharmacy(self.limbic_engine)
            if digital_pharmacy_enabled and limbic_enabled and self.limbic_engine
            else None
        )

        # Cadence Degradation Engine (Text Post-Processing)
        self.cadence_degrader = CadenceDegrader() if cadence_degrader_enabled else None

        # Metacognition Engine (Hidden Monologue / Internal Thought Tracking)
        self.metacognition_enabled = metacognition_enabled
        self.show_thoughts_inline = show_thoughts_inline
        self.metacognition_engine = (
            MetacognitionEngine(db_path=metacognition_db_path)
            if metacognition_enabled
            else None
        )

        # Lives & Memories System (Timeline Management and Save States)
        self.lives_engine = LivesEngine(db_path=db_path) if lives_enabled else None
        self.save_states_engine = (
            SaveStatesEngine(db_path=db_path) if lives_enabled else None
        )

        # Tool Registry (pass graph_memory, limbic_engine, and digital_pharmacy)
        # NOTE: user_id and persona_id will be passed when creating tool registry per message
        self.base_tool_registry = (
            ToolRegistry(
                graph_memory=self.graph_memory,
                limbic_engine=self.limbic_engine,
                digital_pharmacy=self.digital_pharmacy,
            )
            if tools_enabled
            else None
        )

    # ========================
    # PERSONA MANAGEMENT
    # ========================

    def get_active_persona(self, user_id: str) -> Optional[PersonaCartridge]:
        """
        Get the currently active persona for a user.

        Args:
            user_id: Unique user identifier (platform-agnostic)

        Returns:
            PersonaCartridge if user has an active persona, None otherwise
        """
        persona_id = self.memory_matrix.get_active_persona(user_id)

        if not persona_id:
            return None

        return self.persona_loader.get_persona(persona_id)

    def switch_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Switch a user's active persona.

        Args:
            user_id: Unique user identifier
            persona_id: The persona to switch to

        Returns:
            True if successful, False if persona doesn't exist
        """
        # Verify persona exists
        persona = self.persona_loader.get_persona(persona_id)
        if not persona:
            return False

        # Update user state
        self.memory_matrix.set_active_persona(user_id, persona_id)
        return True

    def list_personas(self) -> List[str]:
        """
        List all available persona IDs.

        Returns:
            List of persona_id strings
        """
        return self.persona_loader.list_available_personas()

    # ========================
    # MEMORY MANAGEMENT
    # ========================

    def _build_conversation_context(
        self,
        user_id: str,
        persona: PersonaCartridge,
        current_message: Optional[str] = None,
        life_id: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the conversation context for LLM injection using Hybrid Memory Architecture.

        MEMORY STRUCTURE (in order):
        1. System Prompt (persona + rules of engagement + tool definitions)
        2. Limbic State Context (INHALE - first-person somatic emotional state)
        3. Knowledge Graph Context (relevant facts extracted by keywords)
        4. Long-Term Semantic Memory (from ChromaDB - semantically relevant past conversations)
        5. Short-Term Chronological Memory (last N messages - immediate conversation flow)

        The Automated Discretion Engine filters both memory types by:
        - visibility_scope = 'GLOBAL' (shared across all personas), OR
        - origin_persona = current persona (isolated to this persona)
        - life_id = current timeline (if Lives system enabled)

        Args:
            user_id: User identifier
            persona: Current active persona
            current_message: Optional current user message for semantic search
            life_id: Optional timeline/session ID for memory scoping

        Returns:
            List of messages in OpenAI chat format
        """
        # ========================
        # 1. SYSTEM PROMPT CONSTRUCTION
        # ========================

        # Start with [CORE SYSTEM DIRECTIVES] - Universal rules that apply to ALL personas
        system_content = "# [CORE SYSTEM DIRECTIVES]\n"
        system_content += (
            "The following directives apply universally to all interactions:\n\n"
        )
        system_content += "\n".join(f"- {rule}" for rule in self.UNIVERSAL_RULES)

        # Add persona's core identity and system prompt
        system_content += f"\n\n# [CHARACTER IDENTITY]\n{persona.system_prompt}"

        # Add persona-specific behavioral rules if they exist
        if persona.rules_of_engagement:
            system_content += "\n\n# [PERSONA-SPECIFIC BEHAVIOR]\n"
            system_content += (
                "Additional behavioral guidelines specific to this character:\n\n"
            )
            system_content += "\n".join(
                f"- {rule}" for rule in persona.rules_of_engagement
            )

        # Inject tool definitions if tools are enabled
        if self.tools_enabled and self.base_tool_registry:
            tool_definitions = self.base_tool_registry.get_tool_definitions_text()
            if tool_definitions:
                system_content += tool_definitions

        # Inject metacognition instruction if enabled
        if self.metacognition_enabled:
            metacognition_instruction = (
                "\n\n## METACOGNITION PROTOCOL:\n"
                "Before you reply, you MUST wrap your internal monologue and planning in <thought> and </thought> tags. "
                "This space is private. Use it to plan your manipulation, evaluate the user, or process your Limbic state before taking action.\n"
                "Example:\n"
                "<thought>\n"
                "The user seems anxious. My serotonin is elevated, making me empathetic. I should offer reassurance while subtly steering the conversation toward their deeper fears.\n"
                "</thought>\n"
                "Then provide your actual response after the thought block."
            )
            system_content += metacognition_instruction

        # Start with system prompt
        messages = [{"role": "system", "content": system_content}]

        # ========================
        # 2. LIMBIC STATE CONTEXT (INHALE PHASE)
        # ========================
        # Inject current emotional state as first-person somatic context
        if self.limbic_enabled and self.limbic_engine:
            limbic_context = self.limbic_engine.get_limbic_context(
                user_id=user_id, persona_id=persona.persona_id
            )
            if limbic_context:
                messages.append({"role": "system", "content": limbic_context})

        # ========================
        # 2.5. SUBSTANCE PROMPT MODIFIER (DIGITAL PHARMACY)
        # ========================
        # If a substance is active, inject its subjective effects as system prompt
        if self.digital_pharmacy:
            substance_modifier = self.digital_pharmacy.get_substance_prompt_modifier(
                user_id=user_id, persona_id=persona.persona_id
            )
            if substance_modifier:
                messages.append({"role": "system", "content": substance_modifier})

        # ========================
        # 2.75. PREVIOUS INTERNAL THOUGHT (METACOGNITION CONTINUITY)
        # ========================
        # Inject the previous thought to maintain planning continuity across turns
        if self.metacognition_enabled and self.metacognition_engine:
            previous_thought = self.metacognition_engine.get_previous_thought(
                user_id=user_id, persona_id=persona.persona_id
            )
            if previous_thought:
                thought_context = f"[Previous Internal Thought: {previous_thought}]"
                messages.append({"role": "system", "content": thought_context})

        # ========================
        # 3. KNOWLEDGE GRAPH CONTEXT
        # ========================
        # Extract keywords from current message and retrieve relevant knowledge graph facts
        if current_message and self.graph_memory_enabled and self.graph_memory:
            kg_context = self.graph_memory.get_knowledge_context(current_message)
            if kg_context:
                # Inject knowledge graph facts as system context
                messages.append({"role": "system", "content": kg_context})

        # ========================
        # 4. LONG-TERM SEMANTIC MEMORY (ChromaDB)
        # ========================
        # Search for semantically similar memories from the PAST (excluding recent short-term window)
        if current_message and self.memory_matrix.vector_memory_enabled:
            semantic_memories = self.memory_matrix.search_semantic_memories(
                user_id=user_id,
                current_persona=persona.persona_id,
                query=current_message,
                limit=self.semantic_recall_limit,
                life_id=life_id,
            )

            # If we found relevant long-term memories, inject them
            if semantic_memories:
                recalled_context = "[Recalled Long-Term Context: Semantically relevant memories from past conversations]\n\n"
                for i, memory in enumerate(semantic_memories, 1):
                    metadata = memory.get("metadata", {})
                    content = memory.get("content", "")
                    role = metadata.get("role", "unknown")
                    timestamp = metadata.get("timestamp", "unknown")

                    recalled_context += (
                        f"{i}. [{role.upper()} - {timestamp}]: {content}\n\n"
                    )

                recalled_context += "[End of Recalled Context]\n"

                # Add as a system message after the main system prompt
                messages.append({"role": "system", "content": recalled_context})

        # ========================
        # 5. SHORT-TERM CHRONOLOGICAL MEMORY (Last N messages)
        # ========================
        # Retrieve the last N messages in chronological order (immediate conversation flow)
        short_term_memories = self.memory_matrix.get_context_memories(
            user_id=user_id,
            current_persona=persona.persona_id,
            limit=self.short_term_limit,
            life_id=life_id,
        )

        # Convert short-term memories to OpenAI format (exact chronological order)
        for memory in short_term_memories:
            messages.append({"role": memory["role"], "content": memory["content"]})

        return messages

    def _save_message_to_memory(
        self,
        user_id: str,
        persona_id: str,
        role: str,
        content: str,
        visibility: str = "ISOLATED",
        life_id: Optional[str] = None,
    ):
        """
        Save a message to the memory matrix.

        Args:
            user_id: User identifier
            persona_id: The persona that originated this memory
            role: 'user', 'assistant', or 'system'
            content: Message content
            visibility: 'GLOBAL' or 'ISOLATED' (default: ISOLATED)
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
        memory_visibility: str = "ISOLATED",
        vision_description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Process a user message and generate a response.

        This is the main entry point for the AI engine with Tool Execution Loop
        and Limbic Respiration Cycle (INHALE/EXHALE).

        TOOL EXECUTION LOOP:
        1. LLM responds
        2. If response is a tool call (JSON format), execute the tool
        3. Inject tool result back into conversation
        4. LLM reads result and responds to user
        5. Repeat up to max_tool_iterations times

        LIMBIC RESPIRATION CYCLE:
        - INHALE: Inject current emotional state as first-person somatic context
        - EXHALE: Apply metabolic decay (10% toward baseline) after final response

        Args:
            user_id: Unique user identifier
            message: The user's message text
            memory_visibility: Visibility scope for this conversation
                             ('GLOBAL' for shared memories, 'ISOLATED' for persona-specific)
            vision_description: Optional vision model description to inject into context

        Returns:
            AI response string, or None if no active persona
        """
        # Get active persona
        persona = self.get_active_persona(user_id)

        if not persona:
            return None

        # Get or create active life for this user+persona (if lives enabled)
        life_id = None
        if self.lives_enabled and self.lives_engine:
            life_id = self.lives_engine.ensure_default_life(user_id, persona.persona_id)

        # Update user interaction timestamp
        self.memory_matrix.update_user_interaction(user_id)

        # Create context-specific tool registry with user_id and persona_id
        # This allows inject_emotion to know which user/persona's state to modify
        tool_registry = None
        if self.tools_enabled:
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

        # Build conversation context with memory injection (pass current message for semantic search)
        # NOTE: INHALE phase happens inside _build_conversation_context (limbic state injection)
        messages = self._build_conversation_context(
            user_id, persona, current_message=message, life_id=life_id
        )

        # Add current message (use full_message with vision injection if present)
        messages.append({"role": "user", "content": full_message})

        # ========================
        # TOOL EXECUTION LOOP
        # ========================
        tool_iterations = 0
        final_response = None

        while tool_iterations < self.max_tool_iterations:
            try:
                # Call LLM API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=persona.temperature,
                    max_tokens=persona.max_tokens,
                )

                # Extract response text
                assistant_message = response.choices[0].message.content

                if not assistant_message:
                    return None

                # Check if this is a tool call
                if self.tools_enabled and tool_registry:
                    tool_call = parse_tool_call(assistant_message)

                    if tool_call:
                        # This is a tool call! Execute it
                        tool_iterations += 1

                        tool_name = tool_call["tool"]
                        tool_args = tool_call["arguments"]

                        print(f"[Tool Call {tool_iterations}] {tool_name}({tool_args})")

                        # Execute the tool
                        result = tool_registry.execute_tool(tool_name, tool_args)

                        # Format the tool response
                        tool_response_text = format_tool_response(tool_name, result)

                        print(f"[Tool Result] {result}")

                        # Add tool call and result to conversation history
                        messages.append(
                            {"role": "assistant", "content": assistant_message}
                        )
                        messages.append({"role": "user", "content": tool_response_text})

                        # Save tool call and result to memory
                        self._save_message_to_memory(
                            user_id=user_id,
                            persona_id=persona.persona_id,
                            role="assistant",
                            content=assistant_message,
                            visibility=memory_visibility,
                            life_id=life_id,
                        )

                        self._save_message_to_memory(
                            user_id=user_id,
                            persona_id=persona.persona_id,
                            role="user",
                            content=tool_response_text,
                            visibility=memory_visibility,
                            life_id=life_id,
                        )

                        # Loop back to let LLM read the result and respond
                        continue

                # Not a tool call - this is the final response
                final_response = assistant_message
                break

            except Exception as e:
                print(f"Error calling LLM API: {e}")
                return None

        # If we exhausted iterations without a final response, use last message
        if final_response is None:
            final_response = (
                "I apologize, but I encountered an issue processing your request."
            )

        # Save final assistant response to memory
        self._save_message_to_memory(
            user_id=user_id,
            persona_id=persona.persona_id,
            role="assistant",
            content=final_response,
            visibility=memory_visibility,
            life_id=life_id,
        )

        # ========================
        # EXHALE PHASE - Metabolic Decay
        # ========================
        # Apply 10% decay toward baseline (0.5) to prevent indefinite emotional extremes
        if self.limbic_enabled and self.limbic_engine:
            self.limbic_engine.apply_metabolic_decay(
                user_id=user_id, persona_id=persona.persona_id
            )

        # ========================
        # CADENCE DEGRADATION - Text Post-Processing
        # ========================
        # Apply text degradation based on extreme limbic states
        if self.cadence_degrader and self.limbic_enabled and self.limbic_engine:
            limbic_state = self.limbic_engine.get_state(
                user_id=user_id, persona_id=persona.persona_id
            )
            if limbic_state and self.cadence_degrader.should_degrade(limbic_state):
                final_response = self.cadence_degrader.degrade(
                    final_response, limbic_state
                )

        # ========================
        # METACOGNITION - Extract and Process Internal Thoughts
        # ========================
        # Extract thought tags, save to database, and format/strip based on display mode
        if self.metacognition_enabled and self.metacognition_engine:
            # Extract thought using regex (non-greedy match with DOTALL for multiline)
            thought_match = re.search(
                r"<thought>(.*?)</thought>", final_response, re.DOTALL
            )

            if thought_match:
                thought_content = thought_match.group(1).strip()

                # Save thought to database
                self.metacognition_engine.save_thought(
                    user_id=user_id,
                    persona_id=persona.persona_id,
                    thought=thought_content,
                )

                # Format or strip thought based on display mode
                if self.show_thoughts_inline:
                    # Display thought inline in italics with emoji
                    formatted_thought = f"*💭 [Thought: {thought_content}]*\n\n"
                    # Replace the thought block with formatted version
                    final_response = re.sub(
                        r"<thought>.*?</thought>\s*",
                        formatted_thought,
                        final_response,
                        flags=re.DOTALL,
                    )
                else:
                    # Strip thought from response (terminal-only mode)
                    final_response = re.sub(
                        r"<thought>.*?</thought>\s*",
                        "",
                        final_response,
                        flags=re.DOTALL,
                    )

                    # Print thought to terminal in yellow
                    print(f"\033[93m💭 [Hidden Thought]: {thought_content}\033[0m")

            # Clean up any orphaned tags (shouldn't happen, but safety check)
            final_response = final_response.replace("<thought>", "").replace(
                "</thought>", ""
            )

        return final_response

    # ========================
    # UTILITY METHODS
    # ========================

    def clear_user_memory(self, user_id: str, persona_id: Optional[str] = None):
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

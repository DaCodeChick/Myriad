"""
Context Module - Conversation context assembly for the Hybrid Memory Architecture.

This module was split from conversation_builder.py during RDSSC Phase 1.

Components:
- PromptBuilder: System prompt assembly (persona identity, tools, scenarios)
- MemoryAssembler: Memory retrieval (short-term, semantic, knowledge graph)
- LimbicInjector: Emotional state, substances, metacognition
- ConversationContextBuilder: Main orchestrator (coordinates all components)

Usage:
    from core.context import ConversationContextBuilder
"""

from core.context.context_orchestrator import ConversationContextBuilder
from core.context.prompt_builder import PromptBuilder
from core.context.memory_assembler import MemoryAssembler
from core.context.limbic_injector import LimbicInjector

__all__ = [
    "ConversationContextBuilder",
    "PromptBuilder",
    "MemoryAssembler",
    "LimbicInjector",
]

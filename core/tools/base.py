"""
Base classes and interfaces for Project Myriad's tool system.

Tools are modular, self-contained units that define:
- JSON schema (what parameters they accept)
- Execution logic (what they do)
- Dependencies (what systems they need access to)

Part of RDSSC Phase 7: Modularize tool system for easier extensibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from database.graph_memory import GraphMemory
    from core.features.roleplay.limbic_engine import LimbicEngine
    from core.features.roleplay.limbic_modifiers import DigitalPharmacy
    from core.providers.base import LLMProvider


@dataclass
class ToolContext:
    """
    Context object passed to tools containing system dependencies.

    Tools can access whatever systems they need from this context.
    """

    graph_memory: Optional["GraphMemory"] = None
    limbic_engine: Optional["LimbicEngine"] = None
    digital_pharmacy: Optional["DigitalPharmacy"] = None
    current_user_id: Optional[str] = None
    current_persona_id: Optional[str] = None
    llm_provider: Optional["LLMProvider"] = (
        None  # For tools that need LLM access (e.g., image generation)
    )


class Tool(ABC):
    """
    Abstract base class for all tools.

    Each tool must implement:
    - get_definition(): Returns JSON schema for the tool
    - execute(): Implements the tool's functionality
    """

    def __init__(self, context: ToolContext):
        """
        Initialize the tool with its execution context.

        Args:
            context: ToolContext with system dependencies
        """
        self.context = context

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of this tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what this tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool's parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool with the provided arguments.

        Args:
            **kwargs: Arguments matching the tool's parameter schema

        Returns:
            Tool execution result (any JSON-serializable type)
        """
        pass

    def get_definition(self) -> Dict[str, Any]:
        """
        Get the full tool definition in OpenAI function calling format.

        Returns:
            Tool definition dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def can_execute(self) -> bool:
        """
        Check if this tool can execute given the current context.

        Override this if your tool has specific requirements (e.g., needs graph_memory).

        Returns:
            True if tool can execute, False otherwise
        """
        return True

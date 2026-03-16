"""
Base Feature - Abstract base class for AgentCore feature modules.

Features are pluggable modules that extend AgentCore's capabilities.
Examples: roleplay, code_execution, web_browsing, etc.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseFeature(ABC):
    """
    Abstract base class for AgentCore features.

    Features can:
    - Inject context into prompts
    - Post-process responses
    - Provide tools/commands
    - Maintain their own state
    """

    def __init__(self, config: Any, db_path: str):
        """
        Initialize the feature.

        Args:
            config: Feature-specific configuration object
            db_path: Path to main database (features can use their own tables/DBs)
        """
        self.config = config
        self.db_path = db_path

    @property
    @abstractmethod
    def name(self) -> str:
        """Feature name identifier."""
        pass

    @abstractmethod
    def initialize(self, **dependencies) -> None:
        """
        Initialize the feature with dependencies from AgentCore.

        Args:
            **dependencies: Dict of injected dependencies (providers, services, etc.)
        """
        pass

    def inject_context(
        self, user_id: str, base_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Inject feature-specific context into the conversation context.

        Args:
            user_id: User identifier
            base_context: Base context dict from ConversationContextBuilder

        Returns:
            Modified context dict (can add/modify fields)
        """
        return base_context

    def post_process_response(
        self, user_id: str, response: str, metadata: Dict[str, Any]
    ) -> str:
        """
        Post-process the LLM response before returning.

        Args:
            user_id: User identifier
            response: Raw LLM response text
            metadata: Response metadata (persona, limbic state, etc.)

        Returns:
            Processed response text
        """
        return response

    def get_tools(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Provide feature-specific tools for function calling.

        Args:
            user_id: User identifier

        Returns:
            Dict of tool definitions, or None if no tools
        """
        return None

    def on_message_start(self, user_id: str, message: str) -> None:
        """
        Hook called when a new message is received (before processing).

        Args:
            user_id: User identifier
            message: User's message text
        """
        pass

    def on_message_end(self, user_id: str, response: str) -> None:
        """
        Hook called after response is generated (after post-processing).

        Args:
            user_id: User identifier
            response: Final response text
        """
        pass

    def cleanup(self) -> None:
        """
        Cleanup resources when feature is disabled/unloaded.
        """
        pass

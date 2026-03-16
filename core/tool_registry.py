"""
Tool Registry - Function Calling System for Project Myriad.

This module manages tool definitions and execution for LLM function calling.
Tools are now implemented as modular classes in the core/tools/ directory.

CRITICAL: This module must remain platform-agnostic (no Discord imports).
"""

import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING, Tuple

from core.tools import BUILTIN_TOOLS, ToolContext

if TYPE_CHECKING:
    from database.graph_memory import GraphMemory
    from core.features.roleplay.limbic_engine import LimbicEngine
    from core.features.roleplay.limbic_modifiers import DigitalPharmacy
    from core.tools.base import Tool
    from core.providers.base import LLMProvider


class ToolRegistry:
    """
    Manages tool definitions and execution for LLM function calling.

    Tools are now implemented as modular classes in core/tools/ directory.
    The registry loads and manages these tool instances.
    """

    def __init__(
        self,
        graph_memory: Optional["GraphMemory"] = None,
        limbic_engine: Optional["LimbicEngine"] = None,
        digital_pharmacy: Optional["DigitalPharmacy"] = None,
        current_user_id: Optional[str] = None,
        current_persona_id: Optional[str] = None,
        llm_provider: Optional["LLMProvider"] = None,
    ):
        """
        Initialize the tool registry with available tools.

        Args:
            graph_memory: Optional GraphMemory instance for knowledge graph tools
            limbic_engine: Optional LimbicEngine instance for emotional tools
            digital_pharmacy: Optional DigitalPharmacy instance for substance tools
            current_user_id: Current user ID (needed for inject_emotion context)
            current_persona_id: Current persona ID (needed for inject_emotion context)
            llm_provider: Optional LLM provider instance (for tools like image generation)
        """
        # Create tool context for dependency injection
        self.context = ToolContext(
            graph_memory=graph_memory,
            limbic_engine=limbic_engine,
            digital_pharmacy=digital_pharmacy,
            current_user_id=current_user_id,
            current_persona_id=current_persona_id,
            llm_provider=llm_provider,
        )

        # Storage for tool instances and definitions
        self.tool_instances: Dict[str, "Tool"] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}

        # Storage for generated images (cleared after retrieval)
        self.pending_images: List[Tuple[bytes, str]] = []

        # Load built-in tools
        self._load_builtin_tools()

    def _load_builtin_tools(self) -> None:
        """Load all built-in tools from the core/tools/ directory."""
        for tool_class in BUILTIN_TOOLS:
            # Instantiate the tool with context
            tool_instance = tool_class(self.context)

            # Only register tools that can execute (have required dependencies)
            if tool_instance.can_execute():
                self.tool_instances[tool_instance.name] = tool_instance

                # Build tool definition in OpenAI function calling format
                self.tools[tool_instance.name] = {
                    "type": "function",
                    "function": {
                        "name": tool_instance.name,
                        "description": tool_instance.description,
                        "parameters": tool_instance.parameters,
                    },
                }

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        executor: "Tool",
    ) -> None:
        """
        Register a new tool in the registry.

        This method is kept for backward compatibility but now expects
        a Tool instance rather than a raw function.

        Args:
            name: Unique tool name (used by LLM to call the function)
            description: What the tool does (helps LLM decide when to use it)
            parameters: JSON Schema for the tool's parameters
            executor: Tool instance that executes the tool
        """
        # Store tool instance
        self.tool_instances[name] = executor

        # Store tool definition (OpenAI function calling format)
        self.tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all tool definitions in OpenAI function calling format.

        Returns:
            List of tool definition dictionaries
        """
        return list(self.tools.values())

    def get_tool_definitions_text(self) -> str:
        """
        Get tool definitions as formatted text for injection into system prompt.

        This is used for models that don't support native function calling
        but can follow instructions to output JSON.

        Returns:
            Formatted string describing available tools
        """
        if not self.tools:
            return ""

        tools_text = "\n\n## AVAILABLE TOOLS:\n\n"
        tools_text += "You have access to the following tools. When you need to use a tool, respond with a JSON object in this exact format:\n"
        tools_text += (
            '```json\n{\n  "tool": "tool_name",\n  "arguments": {...}\n}\n```\n\n'
        )
        tools_text += "Available tools:\n\n"

        for tool_name, tool_def in self.tools.items():
            func = tool_def["function"]
            tools_text += f"### {func['name']}\n"
            tools_text += f"**Description:** {func['description']}\n"

            params = func["parameters"]
            if params.get("properties"):
                tools_text += "**Parameters:**\n"
                for param_name, param_info in params["properties"].items():
                    required = (
                        " (required)"
                        if param_name in params.get("required", [])
                        else " (optional)"
                    )
                    tools_text += f"- `{param_name}` ({param_info['type']}){required}: {param_info.get('description', 'No description')}\n"
            else:
                tools_text += "**Parameters:** None\n"

            tools_text += "\n"

        tools_text += "IMPORTANT: If you use a tool, ONLY output the JSON. Do not include any other text before or after the JSON block.\n"

        return tools_text

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the provided arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Dictionary with 'success', 'result', and optional 'error' keys
        """
        if tool_name not in self.tool_instances:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "result": None,
            }

        try:
            # Execute the tool
            tool = self.tool_instances[tool_name]
            result = tool.execute(**arguments)

            return {"success": True, "result": result, "error": None}
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}",
                "result": None,
            }

    async def execute_tool_async(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool asynchronously by name with the provided arguments.

        Stores generated images in self.pending_images for later retrieval.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Dictionary with 'success', 'result', and optional 'error' keys
        """
        if tool_name not in self.tool_instances:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "result": None,
            }

        try:
            tool = self.tool_instances[tool_name]

            # Check if tool has async execution method
            if hasattr(tool, "execute_async"):
                result = await tool.execute_async(**arguments)  # type: ignore
            else:
                # Fall back to sync execution
                result = tool.execute(**arguments)

            # Check if result contains images (from image generation tool)
            if isinstance(result, dict) and "images" in result:
                images = result.get("images", [])
                if images:
                    # Store images for later retrieval
                    self.pending_images.extend(images)

            return {"success": True, "result": result, "error": None}
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}",
                "result": None,
            }

    def get_pending_images(self) -> List[Tuple[bytes, str]]:
        """
        Retrieve and clear pending images from image generation.

        Returns:
            List of (image_bytes, mime_type) tuples
        """
        images = self.pending_images.copy()
        self.pending_images.clear()
        return images


def parse_tool_call(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse LLM response to detect if it's a tool call.

    Looks for JSON in the format:
    {
        "tool": "tool_name",
        "arguments": {...}
    }

    Args:
        response: LLM response text

    Returns:
        Dictionary with 'tool' and 'arguments' if valid tool call,
        None otherwise
    """
    if not response:
        return None

    # Try to extract JSON from response (handle code blocks)
    response = response.strip()

    # Remove markdown code blocks if present
    if response.startswith("```json"):
        response = response[7:]  # Remove ```json
    elif response.startswith("```"):
        response = response[3:]  # Remove ```

    if response.endswith("```"):
        response = response[:-3]  # Remove closing ```

    response = response.strip()

    # Try to parse as JSON
    try:
        data = json.loads(response)

        # Check if it's a valid tool call
        if isinstance(data, dict) and "tool" in data:
            return {"tool": data["tool"], "arguments": data.get("arguments", {})}
    except (json.JSONDecodeError, ValueError):
        # Not a JSON tool call, regular response
        return None

    return None


def format_tool_response(tool_name: str, result: Dict[str, Any]) -> str:
    """
    Format a tool execution result for injection back into conversation.

    Args:
        tool_name: Name of the tool that was executed
        result: Result dictionary from execute_tool()

    Returns:
        Formatted string for LLM to read
    """
    if result["success"]:
        result_text = f"[Tool Response: {tool_name}]\n"
        result_text += f"Result: {json.dumps(result['result'], indent=2)}\n"
        result_text += "[End Tool Response]\n"
    else:
        result_text = f"[Tool Error: {tool_name}]\n"
        result_text += f"Error: {result['error']}\n"
        result_text += "[End Tool Error]\n"

    return result_text

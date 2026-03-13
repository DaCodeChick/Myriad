"""
Tool Registry - Function Calling System for Project Myriad.

This module defines available tools (functions) that the LLM can call,
their JSON schemas, and the execution logic.

CRITICAL: This module must remain platform-agnostic (no Discord imports).
"""

import json
import random
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional


class ToolRegistry:
    """
    Manages tool definitions and execution for LLM function calling.

    Tools are defined with JSON schemas (OpenAI function calling format)
    and mapped to actual Python functions.
    """

    def __init__(self):
        """Initialize the tool registry with available tools."""
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.executors: Dict[str, Callable] = {}

        # Register built-in tools
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register the built-in tools available to all personas."""

        # Tool 1: Get Current Time
        self.register_tool(
            name="get_current_time",
            description="Get the current date and time. Use this when the user asks about the current time, date, day of the week, or any time-related query.",
            parameters={"type": "object", "properties": {}, "required": []},
            executor=self._get_current_time,
        )

        # Tool 2: Roll Dice
        self.register_tool(
            name="roll_dice",
            description="Roll a dice with a specified number of sides. Returns a random number between 1 and the number of sides (inclusive).",
            parameters={
                "type": "object",
                "properties": {
                    "sides": {
                        "type": "integer",
                        "description": "The number of sides on the dice (e.g., 6 for a standard dice, 20 for a D20)",
                        "minimum": 2,
                        "maximum": 1000,
                    }
                },
                "required": ["sides"],
            },
            executor=self._roll_dice,
        )

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        executor: Callable,
    ):
        """
        Register a new tool in the registry.

        Args:
            name: Unique tool name (used by LLM to call the function)
            description: What the tool does (helps LLM decide when to use it)
            parameters: JSON Schema for the tool's parameters
            executor: Python function that executes the tool
        """
        # Store tool definition (OpenAI function calling format)
        self.tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }

        # Store executor function
        self.executors[name] = executor

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
        if tool_name not in self.executors:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "result": None,
            }

        try:
            # Execute the tool
            executor = self.executors[tool_name]
            result = executor(**arguments)

            return {"success": True, "result": result, "error": None}
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}",
                "result": None,
            }

    # ========================
    # BUILT-IN TOOL EXECUTORS
    # ========================

    def _get_current_time(self) -> str:
        """
        Get the current date and time.

        Returns:
            Formatted string with current date and time
        """
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y at %I:%M:%S %p")

    def _roll_dice(self, sides: int) -> Dict[str, Any]:
        """
        Roll a dice with the specified number of sides.

        Args:
            sides: Number of sides on the dice

        Returns:
            Dictionary with roll result and details
        """
        if sides < 2:
            raise ValueError("Dice must have at least 2 sides")
        if sides > 1000:
            raise ValueError("Dice cannot have more than 1000 sides")

        roll = random.randint(1, sides)

        return {
            "roll": roll,
            "sides": sides,
            "description": f"Rolled a D{sides} and got {roll}",
        }


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

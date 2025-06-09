"""
Mock MCP classes for testing without full MCP dependencies.
"""

from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPBaseServer:
    """Mock base class for testing."""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
    
    async def get_tools(self) -> List[Tool]:
        """Return available MCP tools."""
        return []
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Handle tool execution."""
        return f"Mock response for {name}"


def create_tool(name: str, description: str, parameters: Dict[str, Any]) -> Tool:
    """Helper function to create MCP tools."""
    return Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": parameters,
            "required": list(parameters.keys())
        }
    )
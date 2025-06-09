"""
Base MCP server implementation for family AI extensions.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logger = logging.getLogger(__name__)


class MCPBaseServer(ABC):
    """Base class for MCP servers in the family AI extensions."""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.server = Server(name)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools():
            """List available tools."""
            tools = await self.get_tools()
            return [tool.__dict__ for tool in tools]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            """Handle tool calls."""
            try:
                result = await self.call_tool(name, arguments)
                return [{"type": "text", "text": str(result)}]
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [{"type": "text", "text": f"Error: {str(e)}"}]
    
    @abstractmethod
    async def get_tools(self) -> List["Tool"]:
        """Return list of available tools."""
        pass
    
    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Handle tool execution."""
        pass
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server(self.server) as streams:
            await self.server.run(
                streams[0], streams[1], 
                initialization_options={}
            )


class Tool:
    """Simple tool class for MCP compatibility."""
    def __init__(self, name: str, description: str, inputSchema: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema or {}


class ToolRegistry:
    """Registry for managing MCP tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool
    
    def get_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

def create_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any]
) -> Tool:
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
"""MCP Bridge Client - Python package for accessing Dev-Tools MCP gateway"""

from .client import (
    MCPBridgeClient,
    MCPTool,
    MCPToolCompact,
    MCPToolWithDescription,
    ToolDetailLevel,
    ToolInvocationResponse,
)
from .tool_catalog import ToolCatalog
from .progressive_loader import ProgressiveLoader

__version__ = "0.1.0"
__all__ = [
    "MCPBridgeClient",
    "MCPTool",
    "MCPToolCompact",
    "MCPToolWithDescription",
    "ToolDetailLevel",
    "ToolInvocationResponse",
    "ToolCatalog",
    "ProgressiveLoader",
]

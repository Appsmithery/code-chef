"""MCP Bridge Client main implementation"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import httpx

from .tool_catalog import ToolCatalog
from .progressive_loader import ProgressiveLoader


class MCPTool(BaseModel):
    """MCP Tool definition"""
    name: str
    description: str
    server: str
    inputSchema: Optional[Dict[str, Any]] = None


class ToolInvocationResponse(BaseModel):
    """Tool invocation response"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class MCPBridgeClient:
    """
    MCP Bridge Client
    
    Lightweight client for accessing Dev-Tools MCP gateway from any workspace.
    Provides access to 150+ tools across 18 MCP servers without cloning the repo.
    
    Example:
        ```python
        from mcp_bridge_client import MCPBridgeClient
        
        client = MCPBridgeClient(gateway_url='http://45.55.173.72:8000')
        
        # List all tools
        tools = await client.list_tools()
        
        # Search tools by keyword
        memory_tools = await client.search_tools('memory')
        
        # Invoke a tool
        result = await client.invoke_tool('memory/read', {'key': 'user-prefs'})
        ```
    """
    
    def __init__(
        self,
        gateway_url: str = "http://45.55.173.72:8000",
        timeout: float = 30.0,
        enable_caching: bool = True,
        cache_ttl: int = 300,
        progressive_loading: bool = True
    ):
        """
        Initialize MCP Bridge Client
        
        Args:
            gateway_url: MCP gateway endpoint
            timeout: Request timeout in seconds
            enable_caching: Enable tool catalog caching
            cache_ttl: Cache time-to-live in seconds
            progressive_loading: Enable progressive tool loading
        """
        self.gateway_url = gateway_url.rstrip('/')
        self.timeout = timeout
        self.enable_caching = enable_caching
        self.progressive_loading = progressive_loading
        
        self.client = httpx.AsyncClient(
            base_url=self.gateway_url,
            timeout=timeout,
            headers={'Content-Type': 'application/json'}
        )
        
        self.catalog = ToolCatalog(ttl=cache_ttl)
        self.loader = ProgressiveLoader()
    
    async def list_tools(self, force_refresh: bool = False) -> List[MCPTool]:
        """
        List all available MCP tools
        
        Args:
            force_refresh: Bypass cache and fetch fresh data
            
        Returns:
            List of MCP tools
        """
        if not force_refresh and self.enable_caching:
            cached = self.catalog.get_all()
            if cached:
                return cached
        
        response = await self.client.get('/tools')
        response.raise_for_status()
        
        data = response.json()
        tools = [MCPTool(**tool) for tool in data['tools']]
        
        if self.enable_caching:
            self.catalog.set_all(tools)
        
        return tools
    
    async def get_tools_for_task(self, task_description: str) -> List[MCPTool]:
        """
        Get tools relevant to a specific task using progressive loading
        
        Args:
            task_description: Natural language task description
            
        Returns:
            Filtered list of relevant tools
        """
        if not self.progressive_loading:
            return await self.list_tools()
        
        all_tools = await self.list_tools()
        return self.loader.filter_by_task(task_description, all_tools)
    
    async def search_tools(self, query: str) -> List[MCPTool]:
        """
        Search tools by keyword, server, or description
        
        Args:
            query: Search query
            
        Returns:
            Matching tools
        """
        all_tools = await self.list_tools()
        lower_query = query.lower()
        
        return [
            tool for tool in all_tools
            if lower_query in tool.name.lower()
            or lower_query in tool.description.lower()
            or lower_query in tool.server.lower()
        ]
    
    async def get_tools_by_server(self, server_name: str) -> List[MCPTool]:
        """
        Get tools from a specific MCP server
        
        Args:
            server_name: Name of MCP server
            
        Returns:
            Tools from specified server
        """
        all_tools = await self.list_tools()
        return [tool for tool in all_tools if tool.server == server_name]
    
    async def list_servers(self) -> List[str]:
        """
        Get list of available MCP servers
        
        Returns:
            List of server names
        """
        tools = await self.list_tools()
        servers = set(tool.server for tool in tools)
        return sorted(servers)
    
    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> ToolInvocationResponse:
        """
        Invoke an MCP tool
        
        Args:
            tool_name: Name of the tool (e.g., 'memory/read')
            arguments: Tool arguments
            
        Returns:
            Tool invocation result
        """
        try:
            from urllib.parse import quote
            
            response = await self.client.post(
                f'/tools/{quote(tool_name, safe="")}',
                json={'arguments': arguments or {}}
            )
            response.raise_for_status()
            
            data = response.json()
            return ToolInvocationResponse(**data)
        except httpx.HTTPStatusError as e:
            error_msg = e.response.json().get('message', str(e))
            return ToolInvocationResponse(success=False, error=error_msg)
        except Exception as e:
            return ToolInvocationResponse(success=False, error=str(e))
    
    async def health(self) -> Dict[str, Any]:
        """
        Check gateway health
        
        Returns:
            Health status dictionary
        """
        response = await self.client.get('/health')
        response.raise_for_status()
        return response.json()
    
    def clear_cache(self) -> None:
        """Clear tool cache"""
        self.catalog.clear()
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            'gateway_url': self.gateway_url,
            'timeout': self.timeout,
            'enable_caching': self.enable_caching,
            'progressive_loading': self.progressive_loading
        }
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

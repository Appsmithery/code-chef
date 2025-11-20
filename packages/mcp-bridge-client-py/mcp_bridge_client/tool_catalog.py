"""Tool catalog with caching support"""

from typing import Dict, List, Optional
from time import time


class ToolCatalog:
    """Tool catalog with caching support"""
    
    def __init__(self, ttl: int = 300):
        """
        Initialize tool catalog
        
        Args:
            ttl: Cache time-to-live in seconds
        """
        self.tools: List = []
        self.last_update: float = 0
        self.ttl = ttl
    
    def set_all(self, tools: List) -> None:
        """Set all tools in catalog"""
        self.tools = tools
        self.last_update = time()
    
    def get_all(self) -> List:
        """
        Get all tools from catalog
        Returns empty list if cache expired
        """
        if self.is_expired():
            return []
        return self.tools
    
    def is_expired(self) -> bool:
        """Check if cache is expired"""
        return time() - self.last_update > self.ttl
    
    def clear(self) -> None:
        """Clear catalog"""
        self.tools = []
        self.last_update = 0
    
    def get_by_server(self, server_name: str) -> List:
        """Get tools by server"""
        return [t for t in self.tools if t.server == server_name]
    
    def get_by_name(self, tool_name: str) -> Optional[object]:
        """Get tool by name"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def get_stats(self) -> Dict[str, any]:
        """Get catalog statistics"""
        servers = set(t.server for t in self.tools)
        return {
            'total': len(self.tools),
            'servers': len(servers),
            'last_update': self.last_update,
            'expired': self.is_expired()
        }

"""
MCP Server Discovery via Docker MCP Toolkit
Ports functionality from MCPRegistry.js to Python for orchestrator usage
"""

import subprocess
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPToolkitDiscovery:
    """Discovers MCP servers and tools via Docker MCP Toolkit."""

    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.last_refresh: Optional[datetime] = None
        self._check_toolkit_available()

    def _check_toolkit_available(self) -> bool:
        """Check if Docker MCP Toolkit is installed."""
        try:
            result = subprocess.run(
                ["docker", "mcp", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"[MCPDiscovery] Docker MCP Toolkit found: {result.stdout.strip()}")
                return True
            else:
                logger.warning("[MCPDiscovery] Docker MCP Toolkit not available")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"[MCPDiscovery] Failed to check Docker MCP Toolkit: {e}")
            return False

    def discover_servers(self) -> Dict[str, Any]:
        """
        Discover all MCP servers via Docker MCP Toolkit.

        Returns:
            {
                "servers": [
                    {
                        "name": "memory",
                        "tools": ["create_entities", "search_nodes", ...],
                        "tool_count": 9,
                        "status": "running"
                    },
                    ...
                ],
                "total_servers": 17,
                "total_tools": 150,
                "discovered_at": "2025-11-15T..."
            }
        """
        try:
            # Execute: docker mcp server list --json
            result = subprocess.run(
                ["docker", "mcp", "server", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"[MCPDiscovery] Server list failed: {result.stderr}")
                return {"servers": [], "total_servers": 0, "total_tools": 0}

            # Parse server list (returns JSON array of server names)
            server_names = json.loads(result.stdout)

            # Enrich with tool details for each server
            enriched_servers = []
            total_tools = 0

            for server_name in server_names:
                tools = self._get_server_tools(server_name)

                enriched_servers.append({
                    "name": server_name,
                    "tools": tools,
                    "tool_count": len(tools),
                    "status": "available",
                    "type": "stdio"  # Docker MCP Toolkit uses stdio transport
                })

                total_tools += len(tools)

            self.servers = {
                "servers": enriched_servers,
                "total_servers": len(enriched_servers),
                "total_tools": total_tools,
                "discovered_at": datetime.utcnow().isoformat()
            }

            self.last_refresh = datetime.utcnow()
            logger.info(f"[MCPDiscovery] Discovered {len(enriched_servers)} servers with {total_tools} tools")

            return self.servers

        except Exception as e:
            logger.error(f"[MCPDiscovery] Discovery failed: {e}", exc_info=True)
            return {"servers": [], "total_servers": 0, "total_tools": 0}

    def _get_server_tools(self, server_name: str) -> List[str]:
        """Get list of tools for a specific server."""
        try:
            result = subprocess.run(
                ["docker", "mcp", "server", "inspect", server_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"[MCPDiscovery] Failed to get tools for {server_name}")
                return []

            # Parse inspect output to extract tool names
            server_data = json.loads(result.stdout)
            tools = server_data.get("tools", [])
            return [tool["name"] for tool in tools]

        except Exception as e:
            logger.error(f"[MCPDiscovery] Tool enumeration failed for {server_name}: {e}")
            return []

    def get_server(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific server."""
        if not self.servers:
            self.discover_servers()

        for server in self.servers.get("servers", []):
            if server["name"] == server_name:
                return server

        return None

    def get_servers_by_capability(self, capability: str) -> List[str]:
        """
        Get servers that have a specific capability/tool.

        Args:
            capability: Tool name (e.g., "create_entities", "read_file")

        Returns:
            List of server names that provide this tool
        """
        if not self.servers:
            self.discover_servers()

        matching_servers = []
        for server in self.servers.get("servers", []):
            if capability in server.get("tools", []):
                matching_servers.append(server["name"])

        return matching_servers

    def generate_agent_manifest(self) -> Dict[str, Any]:
        """
        Generate agent-to-tool mapping manifest based on discovered servers.

        Uses rules from config/mcp-agent-tool-mapping.yaml to assign tools to agents.
        """
        if not self.servers:
            self.discover_servers()

        # Load agent mapping rules
        import yaml
        from pathlib import Path

        mapping_path = Path(__file__).parent.parent.parent / "config" / "mcp-agent-tool-mapping.yaml"

        try:
            with open(mapping_path, "r") as f:
                mapping_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"[MCPDiscovery] Failed to load agent mapping config: {e}")
            return {}

        # Map agents to discovered servers
        agent_profiles = []

        for agent_name, agent_config in mapping_config.get("agent_tool_mappings", {}).items():
            recommended_tools = []

            for tool_entry in agent_config.get("recommended_tools", []):
                server_name = tool_entry["server"]
                server_info = self.get_server(server_name)

                if server_info:
                    recommended_tools.append({
                        "server": server_name,
                        "tools": tool_entry["tools"],
                        "available": True,
                        "tool_count": len(tool_entry["tools"])
                    })
                else:
                    logger.warning(f"[MCPDiscovery] Server {server_name} not found for agent {agent_name}")
                    recommended_tools.append({
                        "server": server_name,
                        "tools": tool_entry["tools"],
                        "available": False,
                        "tool_count": 0
                    })

            agent_profiles.append({
                "name": agent_name,
                "mission": agent_config.get("mission"),
                "mcp_tools": {
                    "recommended": recommended_tools,
                    "shared": agent_config.get("shared_tools", [])
                },
                "capabilities": self._derive_capabilities(recommended_tools)
            })

        return {
            "version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat(),
            "discovery_summary": self.servers,
            "profiles": agent_profiles
        }

    def _derive_capabilities(self, recommended_tools: List[Dict]) -> List[str]:
        """Derive agent capabilities from assigned tools."""
        capabilities = set()

        capability_map = {
            "memory": ["knowledge_graph", "state_management"],
            "filesystem": ["file_operations", "code_reading"],
            "gitmcp": ["version_control", "code_collaboration"],
            "dockerhub": ["container_management"],
            "playwright": ["browser_automation", "e2e_testing"],
            "notion": ["documentation", "project_management"]
        }

        for tool_entry in recommended_tools:
            server_name = tool_entry["server"]
            if server_name in capability_map:
                capabilities.update(capability_map[server_name])

        return sorted(list(capabilities))


# Singleton instance
_discovery_instance: Optional[MCPToolkitDiscovery] = None


def get_mcp_discovery() -> MCPToolkitDiscovery:
    """Get or create MCP discovery singleton."""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = MCPToolkitDiscovery()
    return _discovery_instance

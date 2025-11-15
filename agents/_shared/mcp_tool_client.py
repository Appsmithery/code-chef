"""
Direct MCP tool invocation using Python MCP SDK.
Replaces HTTP gateway calls with stdio transport to Docker MCP servers.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import asyncio

logger = logging.getLogger(__name__)


class MCPToolClient:
    """
    Direct MCP tool invocation client.

    Uses Python MCP SDK to communicate with servers via stdio transport.
    Note: This implementation uses subprocess-based invocation as the Python MCP SDK
    is still evolving. For production, this can be upgraded to use the official SDK
    when it stabilizes.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.server_connections: Dict[str, Any] = {}
        self._check_mcp_available()

    def _check_mcp_available(self) -> bool:
        """Check if Docker MCP Toolkit is available."""
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "mcp", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"[{self.agent_name}] Docker MCP Toolkit available: {result.stdout.strip()}")
                return True
            else:
                logger.warning(f"[{self.agent_name}] Docker MCP Toolkit not available")
                return False
        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to check MCP availability: {e}")
            return False

    async def invoke_tool(
        self,
        server: str,
        tool: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool on a server.

        Args:
            server: Server name (e.g., "memory", "rust-mcp-filesystem")
            tool: Tool name (e.g., "create_entities", "read_file")
            params: Tool parameters

        Returns:
            Tool execution result
        """
        import subprocess
        import json
        import tempfile

        try:
            # Create input JSON for the tool invocation
            tool_request = {
                "tool": tool,
                "params": params or {}
            }

            # Use docker run to execute the MCP server with the tool
            # This is a simplified approach - in production, maintain persistent connections
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(tool_request, f)
                input_file = f.name

            try:
                # Execute: docker run -i --rm -v input:/input mcp/<server> < input.json
                cmd = [
                    "docker", "run", "-i", "--rm",
                    f"mcp/{server}"
                ]

                with open(input_file, 'r') as stdin_file:
                    result = subprocess.run(
                        cmd,
                        stdin=stdin_file,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                if result.returncode == 0:
                    try:
                        output = json.loads(result.stdout)
                        return {
                            "success": True,
                            "result": output
                        }
                    except json.JSONDecodeError:
                        # Some tools return plain text
                        return {
                            "success": True,
                            "result": result.stdout
                        }
                else:
                    logger.error(f"[{self.agent_name}] Tool invocation failed: {server}/{tool}: {result.stderr}")
                    return {
                        "success": False,
                        "error": result.stderr
                    }

            finally:
                # Clean up temp file
                os.unlink(input_file)

        except subprocess.TimeoutExpired:
            logger.error(f"[{self.agent_name}] Tool invocation timeout: {server}/{tool}")
            return {
                "success": False,
                "error": "Tool invocation timeout"
            }
        except Exception as e:
            logger.error(f"[{self.agent_name}] Tool invocation failed: {server}/{tool}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def invoke_tool_simple(
        self,
        server: str,
        tool: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simplified tool invocation using docker mcp CLI directly.
        This is the recommended approach for Docker MCP Toolkit.

        Args:
            server: Server name (e.g., "memory")
            tool: Tool name (e.g., "create_entities")
            params: Tool parameters as dict

        Returns:
            Tool execution result
        """
        import subprocess
        import json

        try:
            # Build command: docker run -i --rm mcp/<server>
            # Then send JSON-RPC request via stdin
            
            # MCP uses JSON-RPC 2.0 protocol
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": f"tools/{tool}",
                "params": params or {}
            }

            cmd = ["docker", "run", "-i", "--rm", f"mcp/{server}"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send request and get response
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=json.dumps(request).encode()),
                timeout=30.0
            )

            if process.returncode == 0:
                try:
                    response = json.loads(stdout.decode())
                    
                    if "result" in response:
                        return {
                            "success": True,
                            "result": response["result"]
                        }
                    elif "error" in response:
                        return {
                            "success": False,
                            "error": response["error"]
                        }
                    else:
                        return {
                            "success": True,
                            "result": response
                        }
                except json.JSONDecodeError as e:
                    logger.warning(f"[{self.agent_name}] Non-JSON response: {stdout.decode()}")
                    return {
                        "success": True,
                        "result": stdout.decode()
                    }
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"[{self.agent_name}] Tool failed: {server}/{tool}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except asyncio.TimeoutError:
            logger.error(f"[{self.agent_name}] Tool timeout: {server}/{tool}")
            return {
                "success": False,
                "error": "Tool invocation timeout (30s)"
            }
        except Exception as e:
            logger.error(f"[{self.agent_name}] Tool invocation failed: {server}/{tool}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def list_servers(self) -> List[str]:
        """List available MCP servers."""
        from agents._shared.mcp_discovery import get_mcp_discovery

        discovery = get_mcp_discovery()
        servers = discovery.discover_servers()

        return [s["name"] for s in servers.get("servers", [])]

    async def list_tools(self, server: str) -> List[str]:
        """List tools available on a server."""
        from agents._shared.mcp_discovery import get_mcp_discovery

        discovery = get_mcp_discovery()
        server_info = discovery.get_server(server)

        if server_info:
            return server_info.get("tools", [])
        else:
            return []

    async def create_memory_entity(
        self,
        name: str,
        entity_type: str,
        observations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Convenience method: Create an entity in the memory server.

        Args:
            name: Entity name
            entity_type: Entity type
            observations: List of observations about the entity

        Returns:
            Tool execution result
        """
        entity = {
            "name": name,
            "entityType": entity_type,
            "observations": observations or []
        }

        return await self.invoke_tool_simple(
            server="memory",
            tool="create_entities",
            params={"entities": [entity]}
        )

    async def search_memory(self, query: str) -> Dict[str, Any]:
        """
        Convenience method: Search the knowledge graph in memory server.

        Args:
            query: Search query

        Returns:
            Search results
        """
        return await self.invoke_tool_simple(
            server="memory",
            tool="search_nodes",
            params={"query": query}
        )

    async def read_file(self, path: str) -> Dict[str, Any]:
        """
        Convenience method: Read a file using filesystem server.

        Args:
            path: File path to read

        Returns:
            File contents
        """
        return await self.invoke_tool_simple(
            server="rust-mcp-filesystem",
            tool="read_file",
            params={"path": path}
        )

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Convenience method: Write a file using filesystem server.

        Args:
            path: File path to write
            content: File content

        Returns:
            Write result
        """
        return await self.invoke_tool_simple(
            server="rust-mcp-filesystem",
            tool="write_file",
            params={"path": path, "content": content}
        )


# Singleton instances per agent
_tool_clients: Dict[str, MCPToolClient] = {}


def get_mcp_tool_client(agent_name: str) -> MCPToolClient:
    """Get or create MCP tool client for an agent."""
    global _tool_clients
    if agent_name not in _tool_clients:
        _tool_clients[agent_name] = MCPToolClient(agent_name=agent_name)
    return _tool_clients[agent_name]

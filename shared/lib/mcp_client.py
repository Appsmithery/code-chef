"""Shared MCP client utilities for Dev-Tools agents."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import httpx


class MCPClientError(Exception):
    """Base exception for MCP client errors."""


class AgentProfileNotFound(MCPClientError):
    """Raised when an agent profile is missing from the manifest."""


def resolve_manifest_path(preferred_path: Optional[str] = None) -> Path:
    """Resolve the agent manifest path across local and container environments."""

    candidates: List[Path] = []
    seen: set[str] = set()

    def add(path_like: Optional[str | os.PathLike[str]]) -> None:
        if not path_like:
            return
        candidate = Path(path_like).expanduser()
        normalized = candidate.resolve(strict=False)
        key = str(normalized)
        if key in seen:
            return
        seen.add(key)
        candidates.append(normalized)

    add(preferred_path)
    add(os.getenv("AGENT_MANIFEST_PATH"))

    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent

    default_candidates = [
        project_root / "agents-manifest.json",
        base_dir / "agents-manifest.json",
        project_root / "agents" / "agents-manifest.json",
        Path.cwd() / "agents" / "agents-manifest.json",
        Path.cwd() / "agents-manifest.json",
        Path("/app/agents/agents-manifest.json"),
        Path("/agents/agents-manifest.json"),
    ]

    for candidate in default_candidates:
        add(candidate)

    if not candidates:
        add(project_root / "agents-manifest.json")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


class MCPClient:
    """Utility for interacting with the MCP Gateway and agent manifest."""

    _manifest_cache: Optional[Dict[str, Any]] = None
    _manifest_cache_path: Optional[str] = None
    _manifest_mtime: Optional[float] = None
    _cache_lock: Lock = Lock()

    def __init__(
        self,
        agent_name: str,
        manifest_path: Optional[str] = None,
        gateway_url: Optional[
            str
        ] = None,  # Deprecated: kept for backward compatibility
        timeout: Optional[int] = None,
    ) -> None:
        self.agent_name = agent_name
        resolved_path = resolve_manifest_path(manifest_path)
        self.manifest_path = str(resolved_path)
        # Gateway deprecated Dec 2025 - tools accessed via VS Code Docker MCP Toolkit
        self.gateway_url = None  # No longer used
        self.timeout = timeout or int(os.getenv("MCP_TIMEOUT", "30"))

        self.profile = self._load_agent_profile(agent_name)
        self.profile_source = self.profile.get("__source__", "manifest")

    @classmethod
    def _load_manifest(cls, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Agent manifest not found at {path}")

        mtime = os.path.getmtime(path)
        with cls._cache_lock:
            if (
                cls._manifest_cache is not None
                and cls._manifest_cache_path == path
                and cls._manifest_mtime == mtime
            ):
                return cls._manifest_cache

            with open(path, "r", encoding="utf-8-sig") as manifest_file:
                data = json.load(manifest_file)

            cls._manifest_cache = data
            cls._manifest_cache_path = path
            cls._manifest_mtime = mtime
            return data

    def _load_agent_profile(self, agent_name: str) -> Dict[str, Any]:
        try:
            manifest = self._load_manifest(self.manifest_path)
            profiles = manifest.get("profiles", [])
            for profile in profiles:
                if profile.get("name") == agent_name:
                    return profile
        except FileNotFoundError as exc:
            print(f"[MCP] Manifest missing: {exc}")
        except json.JSONDecodeError as exc:
            print(f"[MCP] Manifest parse error: {exc}")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[MCP] Unexpected manifest load error: {exc}")

        # Fallback profile to keep agent operational
        display_name = agent_name.replace("-", " ").title()
        return {
            "name": agent_name,
            "display_name": display_name,
            "capabilities": [],
            "mcp_tools": {"recommended": [], "shared": []},
            "status": "unknown",
            "__source__": "fallback",
        }

    @property
    def recommended_tools(self) -> List[Dict[str, Any]]:
        return self.profile.get("mcp_tools", {}).get("recommended", [])

    @property
    def shared_tools(self) -> List[str]:
        shared = self.profile.get("mcp_tools", {}).get("shared", [])
        return shared if isinstance(shared, list) else []

    @property
    def capabilities(self) -> List[str]:
        caps = self.profile.get("capabilities", [])
        return caps if isinstance(caps, list) else []

    def has_tool(self, server: str, tool: str) -> bool:
        for entry in self.recommended_tools:
            if entry.get("server") == server and tool in entry.get("tools", []):
                return True
        return False

    async def invoke_tool(
        self,
        server: str,
        tool: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Invoke an MCP tool via the gateway."""
        url = f"{self.gateway_url}/tools/{server}/{tool}"
        payload = {"params": params or {}}
        timeout_value = timeout or self.timeout
        try:
            async with httpx.AsyncClient(timeout=timeout_value) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    data.setdefault("success", True)
                    return data
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text,
                }
        except httpx.HTTPError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # pylint: disable=broad-except
            return {"success": False, "error": str(exc)}

    async def get_current_time(self) -> str:
        """Fetch current timestamp from the time server, with fallback."""
        result = await self.invoke_tool("time", "get_current_time")
        if result.get("success"):
            payload = result.get("result")
            if isinstance(payload, dict):
                for key in ("iso_timestamp", "timestamp", "time", "current_time"):
                    if key in payload:
                        return str(payload[key])
            if isinstance(payload, str):
                return payload
        return datetime.utcnow().isoformat()

    async def log_event(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        entity_type: str = "agent_event",
    ) -> bool:
        """Log an event to the shared memory server."""
        metadata = dict(metadata or {})
        metadata.setdefault("agent", self.agent_name)
        metadata.setdefault("event_type", event_type)
        metadata.setdefault("timestamp", await self.get_current_time())

        entity = {
            "name": metadata.get("name")
            or f"{self.agent_name}-{event_type}-{uuid.uuid4().hex[:8]}",
            "type": entity_type,
            "metadata": metadata,
        }

        result = await self.invoke_tool(
            "memory", "create_entities", {"entities": [entity]}
        )
        return result.get("success", False)

    async def get_gateway_health(self) -> Dict[str, Any]:
        """Return MCP gateway health information."""
        url = f"{self.gateway_url}/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "connected",
                        "details": data,
                    }
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "gateway_url": self.gateway_url,
                }
        except httpx.HTTPError as exc:
            return {
                "status": "disconnected",
                "error": str(exc),
                "gateway_url": self.gateway_url,
            }
        except Exception as exc:  # pylint: disable=broad-except
            return {
                "status": "disconnected",
                "error": str(exc),
                "gateway_url": self.gateway_url,
            }

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the agent's MCP configuration."""
        return {
            "agent": self.agent_name,
            "gateway_url": self.gateway_url,
            "recommended_tool_servers": [
                entry.get("server") for entry in self.recommended_tools
            ],
            "shared_tool_servers": self.shared_tools,
            "capabilities": self.capabilities,
            "profile_source": self.profile_source,
        }

    def to_langchain_tools(
        self, toolsets: Optional[List[Dict[str, Any]]] = None
    ) -> List[Any]:
        """Convert MCP tools to LangChain BaseTool instances.

        Args:
            toolsets: Optional list of toolset dicts with 'server' and 'tools' keys.
                     If None, uses recommended_tools from agent profile.

        Returns:
            List of LangChain BaseTool instances that can be bound to LLMs.
        """
        from langchain_core.tools import StructuredTool

        if toolsets is None:
            toolsets = self.recommended_tools

        langchain_tools = []

        for toolset in toolsets:
            server = toolset.get("server")
            tools = toolset.get("tools", [])

            for tool_name in tools:
                # Create a closure to capture server and tool_name
                def make_tool_func(srv: str, tname: str):
                    async def tool_func(**kwargs) -> str:
                        """Invoke MCP tool via gateway."""
                        result = await self.invoke_tool(srv, tname, kwargs)
                        if result.get("success"):
                            return str(result.get("result", ""))
                        return f"Error: {result.get('error', 'Unknown error')}"

                    return tool_func

                # Create LangChain tool
                langchain_tool = StructuredTool.from_function(
                    func=make_tool_func(server, tool_name),
                    name=f"{server}_{tool_name}",
                    description=f"Tool {tool_name} from {server} server",
                    coroutine=make_tool_func(server, tool_name),
                )
                langchain_tools.append(langchain_tool)

        return langchain_tools

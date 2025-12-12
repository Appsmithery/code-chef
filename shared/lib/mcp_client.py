"""Shared MCP client utilities for Dev-Tools agents.

Provides agent manifest loading and profile management.
For MCP tool access, use mcp_tool_client.py with Docker MCP Toolkit.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


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
    """Utility for loading and managing agent profiles from manifest."""

    _manifest_cache: Optional[Dict[str, Any]] = None
    _manifest_cache_path: Optional[str] = None
    _manifest_mtime: Optional[float] = None
    _cache_lock: Lock = Lock()

    def __init__(
        self,
        agent_name: str,
        manifest_path: Optional[str] = None,
    ) -> None:
        """Initialize MCPClient for an agent.

        Args:
            agent_name: Name of the agent (e.g., 'feature_dev', 'code_review')
            manifest_path: Optional path to agents-manifest.json
        """
        self.agent_name = agent_name
        resolved_path = resolve_manifest_path(manifest_path)
        self.manifest_path = str(resolved_path)

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
        """Check if agent profile includes a specific tool.

        Args:
            server: MCP server name (e.g., 'memory', 'filesystem')
            tool: Tool name (e.g., 'create_entities', 'read_file')

        Returns:
            True if tool is in agent's recommended tools
        """
        for entry in self.recommended_tools:
            if entry.get("server") == server and tool in entry.get("tools", []):
                return True
        return False

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the agent's profile configuration.

        Returns:
            Dictionary with agent profile details
        """
        return {
            "agent": self.agent_name,
            "recommended_tool_servers": [
                entry.get("server") for entry in self.recommended_tools
            ],
            "shared_tool_servers": self.shared_tools,
            "capabilities": self.capabilities,
            "profile_source": self.profile_source,
        }

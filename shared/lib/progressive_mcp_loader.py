"""
Progressive MCP Tool Disclosure for Orchestrator Agent

Implements lazy loading of MCP tools based on task requirements to reduce
LLM context size and token costs. Only exposes relevant tools per task.

Based on Anthropic's progressive disclosure pattern:
https://www.anthropic.com/engineering/code-execution-with-mcp
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ToolLoadingStrategy(str, Enum):
    """Strategy for loading MCP tools."""

    MINIMAL = "minimal"  # Only load tools mentioned in task description
    AGENT_PROFILE = "agent_profile"  # Load tools from assigned agent's profile
    PROGRESSIVE = "progressive"  # Start minimal, expand as needed
    FULL = "full"  # Load all 150+ tools (legacy behavior)


@dataclass
class ToolSet:
    """Represents a set of MCP tools for a specific context."""

    server: str
    tools: List[str]
    rationale: str
    priority: str  # critical, high, medium, low


class ProgressiveMCPLoader:
    """
    Manages progressive disclosure of MCP tools to LLM.

    Reduces token usage by only exposing tools relevant to the current task.
    """

    def __init__(
        self,
        mcp_client: Any,  # MCPClient instance
        mcp_discovery: Any,  # MCPToolkitDiscovery instance
        default_strategy: ToolLoadingStrategy = ToolLoadingStrategy.PROGRESSIVE,
    ):
        self.mcp_client = mcp_client
        self.mcp_discovery = mcp_discovery
        self.default_strategy = default_strategy

        # Task-specific keywords mapped to MCP servers
        self.keyword_to_servers = {
            # File operations
            "file": ["rust-mcp-filesystem"],
            "code": ["rust-mcp-filesystem", "gitmcp"],
            "implement": ["rust-mcp-filesystem", "gitmcp"],
            "create": ["rust-mcp-filesystem"],
            "write": ["rust-mcp-filesystem"],
            "read": ["rust-mcp-filesystem"],
            # Version control
            "commit": ["gitmcp"],
            "branch": ["gitmcp"],
            "pull request": ["gitmcp"],
            "pr": ["gitmcp"],
            "git": ["gitmcp"],
            # Containers
            "docker": ["dockerhub"],
            "container": ["dockerhub"],
            "image": ["dockerhub"],
            "deploy": ["dockerhub", "rust-mcp-filesystem"],
            # Documentation & Library Lookup (Context7 integration)
            "document": ["notion", "rust-mcp-filesystem", "context7"],
            "readme": ["rust-mcp-filesystem"],
            "doc": ["notion", "rust-mcp-filesystem", "context7"],
            "api doc": ["notion", "context7"],
            "library": ["context7"],
            "langchain": ["context7"],
            "fastapi": ["context7"],
            "pydantic": ["context7"],
            "openai": ["context7"],
            "anthropic": ["context7"],
            "pytorch": ["context7"],
            "tensorflow": ["context7"],
            "pandas": ["context7"],
            "numpy": ["context7"],
            "react": ["context7"],
            "nextjs": ["context7"],
            "flask": ["context7"],
            "django": ["context7"],
            # Testing
            "test": ["playwright", "rust-mcp-filesystem"],
            "e2e": ["playwright"],
            "selenium": ["playwright"],
            "pytest": ["context7"],
            "jest": ["context7"],
            # Infrastructure
            "terraform": ["rust-mcp-filesystem", "context7"],
            "k8s": ["rust-mcp-filesystem", "context7"],
            "kubernetes": ["rust-mcp-filesystem", "context7"],
            # CI/CD
            "pipeline": ["gitmcp", "rust-mcp-filesystem"],
            "workflow": ["gitmcp", "rust-mcp-filesystem"],
            "github actions": ["gitmcp", "rust-mcp-filesystem"],
            # Monitoring
            "metrics": ["prometheus"],
            "alert": ["prometheus"],
            "monitor": ["prometheus"],
            "grafana": ["context7", "grafana"],
            "prometheus": ["prometheus", "context7"],
            # Communication
            "email": ["gmail-mcp"],
            "notify": ["gmail-mcp", "notion"],
            # Vector DB & RAG
            "qdrant": ["context7"],
            "vector": ["context7"],
            "embedding": ["context7"],
            "rag": ["context7"],
        }

        # Universal tools that are always available (minimal set)
        self.always_available_servers = [
            "memory",  # State management
            "time",  # Timestamps
        ]

    def get_tools_for_task(
        self,
        task_description: str,
        assigned_agent: Optional[str] = None,
        strategy: Optional[ToolLoadingStrategy] = None,
    ) -> List[ToolSet]:
        """
        Get relevant MCP tools for a task using progressive disclosure.

        Args:
            task_description: Natural language task description
            assigned_agent: Agent type handling the task (if known)
            strategy: Override default loading strategy

        Returns:
            List of ToolSet objects with relevant tools
        """
        strategy = strategy or self.default_strategy

        if strategy == ToolLoadingStrategy.MINIMAL:
            return self._get_minimal_tools(task_description)

        elif strategy == ToolLoadingStrategy.AGENT_PROFILE:
            return self._get_agent_profile_tools(assigned_agent)

        elif strategy == ToolLoadingStrategy.PROGRESSIVE:
            return self._get_progressive_tools(task_description, assigned_agent)

        elif strategy == ToolLoadingStrategy.FULL:
            return self._get_all_tools()

        else:
            raise ValueError(f"Unknown loading strategy: {strategy}")

    def _get_minimal_tools(self, task_description: str) -> List[ToolSet]:
        """
        Get minimal tool set based on task keywords.

        Only loads servers mentioned in task description.
        """
        toolsets = []
        description_lower = task_description.lower()

        # Always include universal tools
        for server in self.always_available_servers:
            tools = self._get_server_tools(server)
            if tools:
                toolsets.append(
                    ToolSet(
                        server=server,
                        tools=tools,
                        rationale="Universal tool",
                        priority="critical",
                    )
                )

        # Scan for keyword matches
        matched_servers: Set[str] = set()
        for keyword, servers in self.keyword_to_servers.items():
            if keyword in description_lower:
                matched_servers.update(servers)

        # Load matched servers
        for server in matched_servers:
            tools = self._get_server_tools(server)
            if tools:
                toolsets.append(
                    ToolSet(
                        server=server,
                        tools=tools,
                        rationale=f"Keyword match in task description",
                        priority="high",
                    )
                )

        logger.info(
            f"[ProgressiveMCP] Minimal strategy: loaded {len(toolsets)} servers"
        )
        return toolsets

    def _get_agent_profile_tools(self, agent_name: Optional[str]) -> List[ToolSet]:
        """
        Get tools from agent's profile (recommended + shared).

        Uses config/mcp-agent-tool-mapping.yaml definitions.
        """
        if not agent_name:
            return self._get_minimal_tools("default")

        toolsets = []

        # Get agent profile from MCPClient
        profile = self.mcp_client.profile
        recommended_tools = profile.get("mcp_tools", {}).get("recommended", [])
        shared_tools = profile.get("mcp_tools", {}).get("shared", [])

        # Add recommended tools
        for tool_entry in recommended_tools:
            server = tool_entry.get("server")
            tools = tool_entry.get("tools", [])
            rationale = tool_entry.get("rationale", "Agent profile")
            priority = tool_entry.get("priority", "medium")

            if tools:
                toolsets.append(
                    ToolSet(
                        server=server,
                        tools=tools,
                        rationale=rationale,
                        priority=priority,
                    )
                )

        # Add shared tools (all capabilities)
        for server in shared_tools:
            tools = self._get_server_tools(server)
            if tools:
                toolsets.append(
                    ToolSet(
                        server=server,
                        tools=tools,
                        rationale="Shared agent tool",
                        priority="medium",
                    )
                )

        logger.info(
            f"[ProgressiveMCP] Agent profile strategy: loaded {len(toolsets)} servers for {agent_name}"
        )
        return toolsets

    def _get_progressive_tools(
        self, task_description: str, assigned_agent: Optional[str]
    ) -> List[ToolSet]:
        """
        Progressive disclosure: Start minimal, add agent-specific tools.

        This is the recommended strategy for balancing context and capability.
        """
        # Start with minimal tools based on task
        toolsets = self._get_minimal_tools(task_description)

        # If agent is assigned, add its high-priority tools
        if assigned_agent:
            agent_tools = self._get_agent_profile_tools(assigned_agent)

            # Only add critical/high priority tools from agent profile
            for toolset in agent_tools:
                if toolset.priority in ["critical", "high"]:
                    # Check if server not already loaded
                    if not any(ts.server == toolset.server for ts in toolsets):
                        toolsets.append(toolset)

        logger.info(
            f"[ProgressiveMCP] Progressive strategy: loaded {len(toolsets)} servers"
        )
        return toolsets

    def _get_all_tools(self) -> List[ToolSet]:
        """
        Get all 150+ MCP tools (legacy behavior).

        WARNING: This will consume significant LLM context tokens.
        Only use for debugging or when full capability is required.
        """
        toolsets = []

        # Discover all servers
        servers = self.mcp_discovery.discover_servers()

        for server_info in servers.get("servers", []):
            server_name = server_info["name"]
            tools = server_info.get("tools", [])

            if tools:
                toolsets.append(
                    ToolSet(
                        server=server_name,
                        tools=tools,
                        rationale="Full discovery",
                        priority="low",
                    )
                )

        logger.warning(
            f"[ProgressiveMCP] Full strategy: loaded ALL {len(toolsets)} servers (high token cost)"
        )
        return toolsets

    def _get_server_tools(self, server_name: str) -> List[str]:
        """Get list of tools for a server from discovery."""
        server_info = self.mcp_discovery.get_server(server_name)
        if server_info:
            return server_info.get("tools", [])
        return []

    def format_tools_for_llm(self, toolsets: List[ToolSet]) -> str:
        """
        Format toolsets for LLM context.

        Returns markdown-formatted tool descriptions optimized for LLM consumption.
        """
        lines = ["## Available MCP Tools\n"]

        for toolset in toolsets:
            lines.append(
                f"### Server: `{toolset.server}` ({toolset.priority} priority)"
            )
            lines.append(f"**Purpose:** {toolset.rationale}\n")
            lines.append("**Tools:**")

            for tool in toolset.tools:
                lines.append(f"- `{tool}`")

            lines.append("")  # Empty line between servers

        return "\n".join(lines)

    def format_tools_with_prompts(self, toolsets: List[ToolSet]) -> str:
        """
        Format toolsets with usage examples from .prompt.md files.

        Implements Factor 4 (Tools = JSON) by including standardized tool guides
        with JSON schemas, common patterns, and safety rules.

        Falls back to basic listing if prompt file not found.

        Returns:
            Markdown-formatted tool descriptions with usage examples
        """
        from pathlib import Path

        lines = ["## Available MCP Tools\n"]

        # Map MCP server names to prompt file names
        server_to_prompt = {
            "gitmcp": "git-tools",
            "rust-mcp-filesystem": "filesystem-tools",
            "dockerhub": "docker-tools",
            "linear": "linear-tools",
            "notion": "notion-tools",
            # Add more mappings as tool prompt files are created
        }

        for toolset in toolsets:
            prompt_name = server_to_prompt.get(toolset.server)

            if prompt_name:
                # Try loading tool usage guide from _shared/tool_guides
                prompt_file = (
                    Path(__file__).parent.parent.parent
                    / "agent_orchestrator"
                    / "agents"
                    / "_shared"
                    / "tool_guides"
                    / f"{prompt_name}.prompt.md"
                )

                if prompt_file.exists():
                    lines.append(
                        f"### Server: `{toolset.server}` ({toolset.priority} priority)\n"
                    )
                    lines.append(prompt_file.read_text(encoding="utf-8"))
                    lines.append("")  # Separator
                    continue

            # Fallback to basic listing
            lines.append(
                f"### Server: `{toolset.server}` ({toolset.priority} priority)"
            )
            lines.append(f"**Purpose:** {toolset.rationale}\n")
            lines.append("**Tools:**")

            for tool in toolset.tools:
                lines.append(f"- `{tool}`")

            lines.append("")  # Empty line between servers

        return "\n".join(lines)

    def get_tool_usage_stats(self, toolsets: List[ToolSet]) -> Dict[str, Any]:
        """
        Calculate token savings from progressive disclosure.

        Returns metrics comparing to full tool loading.
        """
        current_tool_count = sum(len(ts.tools) for ts in toolsets)
        current_server_count = len(toolsets)

        # Full discovery baseline
        all_servers = self.mcp_discovery.discover_servers()
        total_tool_count = all_servers.get("total_tools", 150)
        total_server_count = all_servers.get("total_servers", 17)

        token_per_tool = 50  # Rough estimate: tool name + description

        current_tokens = current_tool_count * token_per_tool
        full_tokens = total_tool_count * token_per_tool
        savings = full_tokens - current_tokens
        savings_percent = (savings / full_tokens * 100) if full_tokens > 0 else 0

        return {
            "loaded_tools": current_tool_count,
            "loaded_servers": current_server_count,
            "total_tools": total_tool_count,
            "total_servers": total_server_count,
            "estimated_tokens_used": current_tokens,
            "estimated_tokens_saved": savings,
            "savings_percent": round(savings_percent, 1),
        }


# Convenience function for orchestrator
def get_progressive_loader(mcp_client: Any, mcp_discovery: Any) -> ProgressiveMCPLoader:
    """Factory function to create loader with default settings."""
    return ProgressiveMCPLoader(
        mcp_client=mcp_client,
        mcp_discovery=mcp_discovery,
        default_strategy=ToolLoadingStrategy.PROGRESSIVE,
    )

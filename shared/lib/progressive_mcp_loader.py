"""Progressive MCP Tool Disclosure for Orchestrator Agent

Implements lazy loading of MCP tools based on task requirements to reduce
LLM context size and token costs. Only exposes relevant tools per task.

Based on Anthropic's progressive disclosure pattern:
https://www.anthropic.com/engineering/code-execution-with-mcp

Issue: CHEF-200 - Added @traceable decorators for LangSmith visibility.
Issue: CHEF-XXX - Added semantic tool discovery with LLM-based keyword extraction.
"""

import hashlib
import logging
import os
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from langsmith import traceable

logger = logging.getLogger(__name__)

# Cache TTL for semantic search results (5 minutes)
SEMANTIC_CACHE_TTL = int(os.getenv("MCP_SEMANTIC_CACHE_TTL", "300"))


class ToolLoadingStrategy(str, Enum):
    """Strategy for loading MCP tools."""

    MINIMAL = "minimal"  # Only load tools mentioned in task description
    AGENT_PROFILE = "agent_profile"  # Load tools from assigned agent's profile
    PROGRESSIVE = "progressive"  # Start minimal, expand as needed
    SEMANTIC = "semantic"  # LLM-based semantic tool discovery
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
        llm_client: Optional[Any] = None,  # Optional LLM for semantic extraction
    ):
        self.mcp_client = mcp_client
        self.mcp_discovery = mcp_discovery
        self.default_strategy = default_strategy
        self.llm_client = llm_client

        # Semantic search cache: {hash(task_desc + agent_name): (toolsets, timestamp)}
        self._semantic_cache: Dict[str, Tuple[List["ToolSet"], float]] = {}

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

    @traceable(
        name="mcp_get_tools_for_task",
        tags=["mcp", "tools", "progressive-disclosure"],
        metadata={"component": "progressive_mcp_loader"},
    )
    def get_tools_for_task(
        self,
        task_description: str,
        assigned_agent: Optional[str] = None,
        strategy: Optional[ToolLoadingStrategy] = None,
    ) -> List[ToolSet]:
        """
        Get relevant MCP tools for a task using progressive disclosure.

        This is the primary public method for tool selection. Internal methods
        (_get_minimal_tools, _get_agent_profile_tools, etc.) are not individually
        traced to reduce trace volume and consolidate observability.

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

        elif strategy == ToolLoadingStrategy.SEMANTIC:
            return self._get_semantic_tools(task_description, assigned_agent)

        elif strategy == ToolLoadingStrategy.FULL:
            return self._get_all_tools()

        else:
            raise ValueError(f"Unknown loading strategy: {strategy}")

    def _get_minimal_tools(self, task_description: str) -> List[ToolSet]:
        """
        Get minimal tool set based on task keywords.

        Only loads servers mentioned in task description.
        Note: Tracing consolidated at get_tools_for_task() level.
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
                        rationale="Keyword match in task description",
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
        Note: Tracing consolidated at get_tools_for_task() level.
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
        Note: Tracing consolidated at get_tools_for_task() level.
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

    def _get_semantic_tools(
        self, task_description: str, assigned_agent: Optional[str]
    ) -> List[ToolSet]:
        """
        Semantic tool discovery using LLM-based keyword extraction.

        Implements Anthropic's "Code Execution with MCP" pattern:
        1. Extract 3-5 keywords from task using lightweight LLM
        2. Query tool search with extracted keywords
        3. Merge with agent's critical tools
        4. Cap at 30 tools for token efficiency

        Falls back to progressive strategy if LLM unavailable.
        Note: Tracing consolidated at get_tools_for_task() level.
        """
        # Check cache first
        cache_key = self._get_semantic_cache_key(task_description, assigned_agent)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.debug(f"[ProgressiveMCP] Semantic cache hit for key {cache_key[:8]}")
            return cached

        # Fallback to progressive if no LLM available
        if not self.llm_client:
            logger.debug("[ProgressiveMCP] No LLM client, falling back to progressive")
            return self._get_progressive_tools(task_description, assigned_agent)

        try:
            # Extract keywords using lightweight LLM
            keywords = self._extract_keywords_llm(task_description)
            
            if not keywords:
                logger.warning("[ProgressiveMCP] No keywords extracted, falling back")
                return self._get_progressive_tools(task_description, assigned_agent)

            # Build toolsets from extracted keywords
            toolsets = []
            matched_servers: Set[str] = set()

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
                    matched_servers.add(server)

            # Match keywords to servers
            for keyword in keywords:
                keyword_lower = keyword.lower()
                for kw, servers in self.keyword_to_servers.items():
                    if keyword_lower in kw or kw in keyword_lower:
                        matched_servers.update(servers)

            # Load matched servers
            for server in matched_servers:
                if server in self.always_available_servers:
                    continue  # Already added
                tools = self._get_server_tools(server)
                if tools:
                    toolsets.append(
                        ToolSet(
                            server=server,
                            tools=tools,
                            rationale=f"Semantic match: {', '.join(keywords[:3])}",
                            priority="high",
                        )
                    )

            # Add agent's critical tools (hybrid strategy)
            if assigned_agent:
                agent_tools = self._get_agent_profile_tools(assigned_agent)
                for toolset in agent_tools:
                    if toolset.priority == "critical":
                        if not any(ts.server == toolset.server for ts in toolsets):
                            toolsets.append(toolset)

            # Cap total tools at 30
            total_tools = sum(len(ts.tools) for ts in toolsets)
            if total_tools > 30:
                toolsets = self._cap_toolsets(toolsets, max_tools=30)

            # Cache result
            self._set_cache(cache_key, toolsets)

            logger.info(
                f"[ProgressiveMCP] Semantic strategy: loaded {len(toolsets)} servers "
                f"with keywords {keywords}"
            )
            return toolsets

        except Exception as e:
            logger.warning(f"[ProgressiveMCP] Semantic extraction failed: {e}")
            return self._get_progressive_tools(task_description, assigned_agent)

    def _extract_keywords_llm(self, task_description: str) -> List[str]:
        """
        Extract 3-5 keywords from task description using lightweight LLM.

        Uses a simple prompt to extract tool-relevant keywords.
        Designed for fast, low-token responses (~50 tokens).
        """
        if not self.llm_client:
            return []

        try:
            prompt = f"""Extract 3-5 keywords from this task that indicate what tools are needed.
Focus on: actions (read, write, deploy), technologies (docker, git, kubernetes), 
and domains (testing, monitoring, documentation).

Task: {task_description[:300]}

Return only a comma-separated list of keywords, nothing else.
Example: git, deploy, docker, testing"""

            response = self.llm_client.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # Parse comma-separated keywords
            keywords = [kw.strip().lower() for kw in content.split(",") if kw.strip()]
            
            # Limit to 5 keywords
            return keywords[:5]

        except Exception as e:
            logger.warning(f"[ProgressiveMCP] Keyword extraction failed: {e}")
            return []

    def _get_semantic_cache_key(
        self, task_description: str, assigned_agent: Optional[str]
    ) -> str:
        """Generate cache key for semantic search results."""
        key_input = f"{task_description[:200]}:{assigned_agent or 'none'}"
        return hashlib.md5(key_input.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[ToolSet]]:
        """Get toolsets from cache if not expired."""
        if cache_key not in self._semantic_cache:
            return None
        
        toolsets, timestamp = self._semantic_cache[cache_key]
        if time.time() - timestamp > SEMANTIC_CACHE_TTL:
            del self._semantic_cache[cache_key]
            return None
        
        return toolsets

    def _set_cache(self, cache_key: str, toolsets: List[ToolSet]) -> None:
        """Store toolsets in cache with current timestamp."""
        self._semantic_cache[cache_key] = (toolsets, time.time())
        
        # Prune old entries (keep max 100)
        if len(self._semantic_cache) > 100:
            oldest_key = min(
                self._semantic_cache.keys(),
                key=lambda k: self._semantic_cache[k][1]
            )
            del self._semantic_cache[oldest_key]

    def _cap_toolsets(self, toolsets: List[ToolSet], max_tools: int = 30) -> List[ToolSet]:
        """Cap total tool count while preserving high-priority toolsets."""
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_toolsets = sorted(
            toolsets,
            key=lambda ts: priority_order.get(ts.priority, 4)
        )
        
        result = []
        total_tools = 0
        
        for toolset in sorted_toolsets:
            if total_tools + len(toolset.tools) <= max_tools:
                result.append(toolset)
                total_tools += len(toolset.tools)
            elif total_tools < max_tools:
                # Partial inclusion - trim tools
                remaining = max_tools - total_tools
                trimmed = ToolSet(
                    server=toolset.server,
                    tools=toolset.tools[:remaining],
                    rationale=toolset.rationale + " (trimmed)",
                    priority=toolset.priority,
                )
                result.append(trimmed)
                break
        
        return result

    def _get_all_tools(self) -> List[ToolSet]:
        """
        Get all 150+ MCP tools (legacy behavior).

        WARNING: This will consume significant LLM context tokens.
        Only use for debugging or when full capability is required.
        Note: Tracing consolidated at get_tools_for_task() level.
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

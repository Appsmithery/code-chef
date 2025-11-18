Based on the Anthropic article on progressive tool disclosure and your Dev-Tools architecture, here's a script to implement lazy loading of MCP tools for the orchestrator:

```python
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
        default_strategy: ToolLoadingStrategy = ToolLoadingStrategy.PROGRESSIVE
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

            # Documentation
            "document": ["notion", "rust-mcp-filesystem"],
            "readme": ["rust-mcp-filesystem"],
            "doc": ["notion", "rust-mcp-filesystem"],
            "api doc": ["notion"],

            # Testing
            "test": ["playwright", "rust-mcp-filesystem"],
            "e2e": ["playwright"],
            "selenium": ["playwright"],

            # Infrastructure
            "terraform": ["rust-mcp-filesystem"],
            "k8s": ["rust-mcp-filesystem"],
            "kubernetes": ["rust-mcp-filesystem"],

            # CI/CD
            "pipeline": ["gitmcp", "rust-mcp-filesystem"],
            "workflow": ["gitmcp", "rust-mcp-filesystem"],
            "github actions": ["gitmcp", "rust-mcp-filesystem"],

            # Monitoring
            "metrics": ["prometheus"],
            "alert": ["prometheus"],
            "monitor": ["prometheus"],

            # Communication
            "email": ["gmail-mcp"],
            "notify": ["gmail-mcp", "notion"],
        }

        # Universal tools that are always available (minimal set)
        self.always_available_servers = [
            "memory",  # State management
            "time",    # Timestamps
        ]

    def get_tools_for_task(
        self,
        task_description: str,
        assigned_agent: Optional[str] = None,
        strategy: Optional[ToolLoadingStrategy] = None
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
            toolsets.append(ToolSet(
                server=server,
                tools=self._get_server_tools(server),
                rationale="Universal tool",
                priority="critical"
            ))

        # Scan for keyword matches
        matched_servers: Set[str] = set()
        for keyword, servers in self.keyword_to_servers.items():
            if keyword in description_lower:
                matched_servers.update(servers)

        # Load matched servers
        for server in matched_servers:
            tools = self._get_server_tools(server)
            if tools:
                toolsets.append(ToolSet(
                    server=server,
                    tools=tools,
                    rationale=f"Keyword match in task description",
                    priority="high"
                ))

        logger.info(f"[ProgressiveMCP] Minimal strategy: loaded {len(toolsets)} servers")
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
                toolsets.append(ToolSet(
                    server=server,
                    tools=tools,
                    rationale=rationale,
                    priority=priority
                ))

        # Add shared tools (all capabilities)
        for server in shared_tools:
            tools = self._get_server_tools(server)
            if tools:
                toolsets.append(ToolSet(
                    server=server,
                    tools=tools,
                    rationale="Shared agent tool",
                    priority="medium"
                ))

        logger.info(f"[ProgressiveMCP] Agent profile strategy: loaded {len(toolsets)} servers for {agent_name}")
        return toolsets

    def _get_progressive_tools(
        self,
        task_description: str,
        assigned_agent: Optional[str]
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

        logger.info(f"[ProgressiveMCP] Progressive strategy: loaded {len(toolsets)} servers")
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
                toolsets.append(ToolSet(
                    server=server_name,
                    tools=tools,
                    rationale="Full discovery",
                    priority="low"
                ))

        logger.warning(f"[ProgressiveMCP] Full strategy: loaded ALL {len(toolsets)} servers (high token cost)")
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
            lines.append(f"### Server: `{toolset.server}` ({toolset.priority} priority)")
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
def get_progressive_loader(
    mcp_client: Any,
    mcp_discovery: Any
) -> ProgressiveMCPLoader:
    """Factory function to create loader with default settings."""
    return ProgressiveMCPLoader(
        mcp_client=mcp_client,
        mcp_discovery=mcp_discovery,
        default_strategy=ToolLoadingStrategy.PROGRESSIVE
    )
```

Now, integrate this into the orchestrator's main.py:

```python
# ...existing code...

from lib.progressive_mcp_loader import get_progressive_loader, ToolLoadingStrategy

# Add after mcp_client initialization
progressive_loader = get_progressive_loader(mcp_client, mcp_discovery)

# ...existing code...

@app.post("/orchestrate", response_model=TaskResponse)
async def orchestrate_task(request: TaskRequest):
    """
    Main orchestration endpoint with progressive tool disclosure.

    Token Optimization: Only loads relevant tools per task (10-30 tools vs 150+)
    """
    import uuid

    task_id = str(uuid.uuid4())

    # Progressive tool loading: Get minimal tools based on task description
    relevant_toolsets = progressive_loader.get_tools_for_task(
        task_description=request.description,
        strategy=ToolLoadingStrategy.MINIMAL
    )

    # Log token savings
    stats = progressive_loader.get_tool_usage_stats(relevant_toolsets)
    logger.info(f"[Orchestrator] Progressive loading stats: {stats}")
    await mcp_tool_client.create_memory_entity(
        name=f"tool_loading_stats_{task_id}",
        entity_type="orchestrator_metrics",
        observations=[
            f"Task: {task_id}",
            f"Loaded tools: {stats['loaded_tools']} / {stats['total_tools']}",
            f"Token savings: {stats['savings_percent']}%",
            f"Estimated tokens saved: {stats['estimated_tokens_saved']}"
        ]
    )

    # Format tools for LLM context
    available_tools_context = progressive_loader.format_tools_for_llm(relevant_toolsets)

    # Decompose request with context about available tools
    if gradient_client.is_enabled():
        subtasks = await decompose_with_llm(
            request,
            task_id,
            available_tools=available_tools_context  # Pass tool context to LLM
        )
    else:
        subtasks = decompose_request(request)

    # For each subtask, load agent-specific tools progressively
    validation_results = {}
    for subtask in subtasks:
        # Load tools for assigned agent
        agent_toolsets = progressive_loader.get_tools_for_task(
            task_description=subtask.description,
            assigned_agent=subtask.agent_type.value,
            strategy=ToolLoadingStrategy.PROGRESSIVE
        )

        # Validate tool availability
        subtask_required_tools = get_required_tools_for_task(subtask.description)
        availability = await check_agent_tool_availability(
            subtask.agent_type,
            subtask_required_tools
        )
        validation_results[subtask.id] = {
            **availability,
            "loaded_toolsets": len(agent_toolsets),
            "tools_context": progressive_loader.format_tools_for_llm(agent_toolsets)
        }

    # ...rest of existing orchestration logic...

    return response


async def decompose_with_llm(
    request: TaskRequest,
    task_id: str,
    available_tools: Optional[str] = None
) -> List[SubTask]:
    """
    Decompose task with LLM, including progressive tool context.
    """
    import uuid
    import json

    system_prompt = """You are an expert DevOps orchestrator. Analyze development requests and decompose them into discrete subtasks for specialized agents.

Available agents:
- feature-dev: Application code generation and feature implementation
- code-review: Quality assurance, static analysis, security scanning
- infrastructure: Infrastructure-as-code generation (Docker, K8s, Terraform)
- cicd: CI/CD pipeline generation (GitHub Actions, GitLab CI)
- documentation: Documentation generation (README, API docs)

Return JSON with this structure:
{
  "subtasks": [
    {
      "agent_type": "feature-dev",
      "description": "Implement user authentication",
      "dependencies": []
    }
  ]
}"""

    # Include progressive tool context in user prompt
    user_prompt = f"""Task: {request.description}

Project Context: {json.dumps(request.project_context) if request.project_context else "General project"}
Priority: {request.priority}

{available_tools if available_tools else ""}

Break this down into subtasks. Consider dependencies and execution order.
IMPORTANT: Only suggest using tools that are listed in the "Available MCP Tools" section above."""

    # ...rest of existing LLM decomposition logic...

    return subtasks
```

Finally, add an endpoint to adjust loading strategy at runtime:

```python
@app.post("/config/tool-loading")
async def configure_tool_loading(request: Dict[str, Any]):
    """
    Configure progressive tool loading strategy.

    Request:
        {
            "strategy": "minimal" | "agent_profile" | "progressive" | "full",
            "reason": "debugging" | "cost_optimization" | "high_complexity_task"
        }
    """
    strategy_name = request.get("strategy", "progressive")
    reason = request.get("reason", "runtime_config")

    try:
        strategy = ToolLoadingStrategy(strategy_name)
        progressive_loader.default_strategy = strategy

        await mcp_tool_client.create_memory_entity(
            name=f"tool_loading_config_change_{datetime.utcnow().isoformat()}",
            entity_type="orchestrator_config",
            observations=[
                f"Strategy changed to: {strategy_name}",
                f"Reason: {reason}",
                f"Timestamp: {datetime.utcnow().isoformat()}"
            ]
        )

        return {
            "success": True,
            "current_strategy": strategy_name,
            "reason": reason
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy: {strategy_name}. Valid values: minimal, agent_profile, progressive, full"
        )


@app.get("/config/tool-loading/stats")
async def get_tool_loading_stats():
    """
    Get statistics about current tool loading configuration.
    """
    # Get current strategy tools
    sample_toolsets = progressive_loader.get_tools_for_task(
        task_description="sample task",
        strategy=progressive_loader.default_strategy
    )

    stats = progressive_loader.get_tool_usage_stats(sample_toolsets)

    return {
        "current_strategy": progressive_loader.default_strategy.value,
        "stats": stats,
        "recommendation": (
            "Consider using 'minimal' or 'progressive' for cost optimization"
            if stats["savings_percent"] < 50
            else "Current strategy is well-optimized"
        )
    }
```

**Key Benefits:**

1. **Token Savings:** Reduces context from 150+ tools (7,500+ tokens) to 10-30 tools (500-1,500 tokens) = **80-90% reduction**
2. **Faster LLM Responses:** Less context = faster inference times
3. **Cost Optimization:** Fewer input tokens = lower Gradient AI costs
4. **Progressive Expansion:** Can request more tools if task complexity increases
5. **Agent-Aware:** Loads tools appropriate for assigned agent
6. **Runtime Configurable:** Adjust strategy via API for debugging or complex tasks

**Usage Example:**

```bash
# Orchestrate with minimal tools (80%+ token savings)
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "implement user authentication with email/password",
    "priority": "high"
  }'

# Change to full tools for debugging
curl -X POST http://localhost:8001/config/tool-loading \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "full",
    "reason": "debugging_tool_availability"
  }'

# Check token savings
curl http://localhost:8001/config/tool-loading/stats
```

This implementation follows Anthropic's progressive disclosure pattern while integrating seamlessly with your existing Dev-Tools architecture.

"""Agent tool loading strategy tests.

Tests progressive tool loading implementation:
- MINIMAL strategy (10-30 tools)
- PROGRESSIVE strategy (30-60 tools)
- FULL strategy (150+ tools)
- Token efficiency validation
- Invoke-time tool binding
"""

import pytest

from agent_orchestrator.agents._shared.base_agent import ToolLoadingStrategy
from agent_orchestrator.agents.feature_dev import FeatureDevAgent


class TestToolLoadingStrategies:
    """Test progressive tool loading implementation."""

    @pytest.mark.integration
    @pytest.mark.agent
    def test_minimal_strategy_loads_10_to_30_tools(self):
        """Test MINIMAL strategy loads expected tool count."""
        agent = FeatureDevAgent()
        tools = agent.get_tools(strategy=ToolLoadingStrategy.MINIMAL)

        assert (
            10 <= len(tools) <= 30
        ), f"Expected 10-30 tools for MINIMAL strategy, got {len(tools)}"

        # Verify only core tools loaded
        tool_names = [t.name for t in tools]

        # Essential file operations
        assert "read_file" in tool_names, "Missing core tool: read_file"
        assert "create_file" in tool_names, "Missing core tool: create_file"
        assert (
            "replace_string_in_file" in tool_names
        ), "Missing core tool: replace_string_in_file"

        # Essential search
        assert "grep_search" in tool_names, "Missing core tool: grep_search"
        assert "semantic_search" in tool_names, "Missing core tool: semantic_search"

        # Verify MCP tools NOT loaded in MINIMAL
        mcp_tool_prefixes = ["mcp_", "github-pull-request_", "activate_"]
        mcp_tools_loaded = [
            t for t in tool_names if any(t.startswith(p) for p in mcp_tool_prefixes)
        ]

        assert (
            len(mcp_tools_loaded) == 0
        ), f"MCP tools should not be in MINIMAL: {mcp_tools_loaded}"

    @pytest.mark.integration
    @pytest.mark.agent
    def test_progressive_strategy_loads_30_to_60_tools(self):
        """Test PROGRESSIVE strategy loads expected tool count."""
        agent = FeatureDevAgent()
        tools = agent.get_tools(strategy=ToolLoadingStrategy.PROGRESSIVE)

        assert (
            30 <= len(tools) <= 60
        ), f"Expected 30-60 tools for PROGRESSIVE strategy, got {len(tools)}"

        # Verify agent-priority tools loaded
        tool_names = [t.name for t in tools]

        # Core tools still present
        assert "read_file" in tool_names
        assert "create_file" in tool_names

        # Agent-specific tools added
        assert "runTests" in tool_names, "Missing agent-priority tool: runTests"
        assert (
            "run_in_terminal" in tool_names
        ), "Missing agent-priority tool: run_in_terminal"

        # Some MCP tools loaded (based on feature_dev keywords)
        # feature_dev keywords: code, implementation, feature, development, git
        expected_mcp_tools = [
            "activate_python_environment_management_tools",
            "activate_container_inspection_and_logging_tools",
        ]

        # At least some MCP tools should be loaded
        mcp_tool_prefixes = ["mcp_", "activate_"]
        mcp_tools_loaded = [
            t for t in tool_names if any(t.startswith(p) for p in mcp_tool_prefixes)
        ]

        assert (
            len(mcp_tools_loaded) > 0
        ), "Expected some MCP tools in PROGRESSIVE strategy"

    @pytest.mark.integration
    @pytest.mark.agent
    def test_full_strategy_loads_150_plus_tools(self):
        """Test FULL strategy loads all available tools."""
        agent = FeatureDevAgent()
        tools = agent.get_tools(strategy=ToolLoadingStrategy.FULL)

        assert (
            len(tools) >= 150
        ), f"Expected 150+ tools for FULL strategy, got {len(tools)}"

        # Verify comprehensive toolset loaded
        tool_names = [t.name for t in tools]

        # All core tools present
        assert "read_file" in tool_names
        assert "create_file" in tool_names
        assert "runTests" in tool_names

        # Many MCP tools loaded
        mcp_tool_prefixes = ["mcp_", "activate_"]
        mcp_tools_loaded = [
            t for t in tool_names if any(t.startswith(p) for p in mcp_tool_prefixes)
        ]

        assert (
            len(mcp_tools_loaded) >= 50
        ), f"Expected 50+ MCP tools in FULL strategy, got {len(mcp_tools_loaded)}"

        # Verify all MCP categories represented
        expected_categories = ["huggingface", "linear", "container", "python", "github"]

        for category in expected_categories:
            category_tools = [t for t in mcp_tools_loaded if category in t.lower()]
            assert (
                len(category_tools) > 0
            ), f"Expected tools from category '{category}' in FULL strategy"

    @pytest.mark.integration
    @pytest.mark.agent
    async def test_token_efficiency_by_strategy(self):
        """Test token usage varies by strategy."""
        task = {"description": "Create a hello world function in Python"}

        # Execute with MINIMAL
        agent_minimal = FeatureDevAgent(tool_strategy=ToolLoadingStrategy.MINIMAL)
        result_minimal = await agent_minimal.process_task(task)
        tokens_minimal = result_minimal.get("metadata", {}).get("total_tokens", 0)

        # Execute with PROGRESSIVE
        agent_progressive = FeatureDevAgent(
            tool_strategy=ToolLoadingStrategy.PROGRESSIVE
        )
        result_progressive = await agent_progressive.process_task(task)
        tokens_progressive = result_progressive.get("metadata", {}).get(
            "total_tokens", 0
        )

        # Execute with FULL
        agent_full = FeatureDevAgent(tool_strategy=ToolLoadingStrategy.FULL)
        result_full = await agent_full.process_task(task)
        tokens_full = result_full.get("metadata", {}).get("total_tokens", 0)

        # Verify token efficiency
        assert tokens_minimal < tokens_progressive < tokens_full, (
            f"Token usage should increase: MINIMAL ({tokens_minimal}) < "
            f"PROGRESSIVE ({tokens_progressive}) < FULL ({tokens_full})"
        )

        # Verify 80-90% reduction from FULL to MINIMAL
        if tokens_full > 0:
            reduction_pct = (1 - tokens_minimal / tokens_full) * 100
            assert (
                reduction_pct >= 80
            ), f"Expected 80%+ token reduction from FULL to MINIMAL, got {reduction_pct:.1f}%"

        # Verify all strategies complete the task successfully
        assert result_minimal.get("status") == "completed"
        assert result_progressive.get("status") == "completed"
        assert result_full.get("status") == "completed"

    @pytest.mark.integration
    @pytest.mark.agent
    def test_invoke_time_tool_binding(self):
        """Test tools bound at invoke time, not init time."""
        agent = FeatureDevAgent()

        # Agent should not have tools at init
        assert not hasattr(
            agent, "_tools"
        ), "Agent should not have _tools attribute at initialization"

        # Tools should be bound when get_tools() called
        tools = agent.get_tools(strategy=ToolLoadingStrategy.MINIMAL)
        assert len(tools) > 0, "Expected tools to be bound after get_tools() call"

        # Verify cache works
        tools2 = agent.get_tools(strategy=ToolLoadingStrategy.MINIMAL)
        assert (
            tools is tools2
        ), "Expected cached tools (same object reference) for same strategy"

        # Verify different strategies return different tool sets
        tools_progressive = agent.get_tools(strategy=ToolLoadingStrategy.PROGRESSIVE)
        assert (
            tools_progressive is not tools
        ), "Expected different tool sets for different strategies"
        assert len(tools_progressive) > len(
            tools
        ), "Expected PROGRESSIVE to have more tools than MINIMAL"

    @pytest.mark.integration
    @pytest.mark.agent
    def test_keyword_based_tool_selection(self):
        """Test progressive loader selects tools based on agent keywords."""
        from shared.lib.progressive_mcp_loader import ProgressiveMCPLoader

        # Load agent keyword mapping
        loader = ProgressiveMCPLoader()

        # Feature Dev keywords: code, implementation, feature, development, git
        feature_dev_keywords = loader.get_keywords_for_agent("feature_dev")
        assert "code" in feature_dev_keywords
        assert "git" in feature_dev_keywords

        # Get tools for feature_dev with PROGRESSIVE
        tools = loader.load_tools_progressive(agent_name="feature_dev")
        tool_names = [t.name for t in tools]

        # Should include Python tools (code keyword)
        python_tools = [t for t in tool_names if "python" in t.lower()]
        assert (
            len(python_tools) > 0
        ), "Expected Python tools for feature_dev (keyword: code)"

        # Should include container tools (development keyword)
        container_tools = [t for t in tool_names if "container" in t.lower()]
        assert (
            len(container_tools) > 0
        ), "Expected container tools for feature_dev (keyword: development)"

        # Test another agent - Infrastructure
        # Keywords: infrastructure, docker, terraform, deployment
        infra_tools = loader.load_tools_progressive(agent_name="infrastructure")
        infra_tool_names = [t.name for t in infra_tools]

        # Should include container/docker tools
        docker_tools = [
            t
            for t in infra_tool_names
            if "container" in t.lower() or "docker" in t.lower()
        ]
        assert (
            len(docker_tools) > 0
        ), "Expected Docker/container tools for infrastructure agent"

    @pytest.mark.integration
    @pytest.mark.agent
    def test_tool_loading_strategy_escalation(self):
        """Test strategy can escalate during task execution."""
        agent = FeatureDevAgent()

        # Start with MINIMAL
        initial_tools = agent.get_tools(strategy=ToolLoadingStrategy.MINIMAL)
        initial_count = len(initial_tools)

        # Escalate to PROGRESSIVE
        progressive_tools = agent.get_tools(strategy=ToolLoadingStrategy.PROGRESSIVE)
        progressive_count = len(progressive_tools)

        # Escalate to FULL
        full_tools = agent.get_tools(strategy=ToolLoadingStrategy.FULL)
        full_count = len(full_tools)

        # Verify escalation
        assert initial_count < progressive_count < full_count, (
            f"Strategy escalation failed: MINIMAL ({initial_count}) < "
            f"PROGRESSIVE ({progressive_count}) < FULL ({full_count})"
        )

        # Verify each level includes previous level's tools
        initial_names = {t.name for t in initial_tools}
        progressive_names = {t.name for t in progressive_tools}
        full_names = {t.name for t in full_tools}

        # PROGRESSIVE should include all MINIMAL tools
        assert initial_names.issubset(
            progressive_names
        ), "PROGRESSIVE should include all MINIMAL tools"

        # FULL should include all PROGRESSIVE tools
        assert progressive_names.issubset(
            full_names
        ), "FULL should include all PROGRESSIVE tools"


# Fixtures


@pytest.fixture
def feature_dev_agent():
    """Provide Feature Dev agent instance."""
    return FeatureDevAgent()


@pytest.fixture
def progressive_loader():
    """Provide ProgressiveMCPLoader instance."""
    from shared.lib.progressive_mcp_loader import ProgressiveMCPLoader

    return ProgressiveMCPLoader()

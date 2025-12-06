"""Base agent class for LangGraph agent nodes."""

import sys
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langsmith import traceable

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from lib.mcp_client import MCPClient
from lib.gradient_client import get_gradient_client
from lib.progressive_mcp_loader import ProgressiveMCPLoader, ToolLoadingStrategy

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for LangGraph agent nodes.

    Each agent node:
    1. Loads configuration from YAML file (model, tools, prompts)
    2. Initializes MCP client for tool access
    3. Initializes LLM with model-specific settings
    4. Binds tools to LLM for function calling
    5. Provides invoke() method for graph execution
    """

    def __init__(self, config_path: str, agent_name: str):
        """Initialize agent from configuration file.

        Args:
            config_path: Path to agent YAML configuration file
            agent_name: Name of the agent (for MCP client and tracing)
        """
        self.agent_name = agent_name
        self.config = self._load_config(config_path)

        # Initialize MCP client for tool access
        self.mcp_client = MCPClient(agent_name=agent_name)

        # Initialize progressive tool loader (skip if mcp_discovery not available)
        try:
            from lib.mcp_discovery import get_mcp_discovery

            mcp_discovery = get_mcp_discovery()
            self.tool_loader = ProgressiveMCPLoader(self.mcp_client, mcp_discovery)
        except Exception as e:
            logger.warning(f"Progressive tool loader unavailable: {e}")
            self.tool_loader = None

        # Initialize LLM with agent-specific model
        self.llm = self._initialize_llm()

        # Bind tools to LLM
        self.agent_executor = self._bind_tools()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load agent configuration from YAML file.

        Expected YAML structure:
        ```yaml
        agent:
          name: feature-dev
          model: codellama-13b
          temperature: 0.7
          max_tokens: 2000
          system_prompt: |
            You are a senior Python developer...

        tools:
          progressive_strategy: MINIMAL
          allowed_servers:
            - github
            - filesystem
            - git

        langsmith:
          project: code-chef-feature-dev
          tags: [feature-development]
        ```
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Agent config not found: {config_path}")

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required_fields = ["agent", "tools"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in {config_path}")

        return config

    def _initialize_llm(self) -> BaseChatModel | Any:
        """Initialize LLM with agent-specific configuration."""
        agent_config = self.config["agent"]

        # Get Gradient client with agent-specific model
        gradient_client = get_gradient_client(
            agent_name=self.agent_name, model=agent_config.get("model", "llama-3.1-8b")
        )

        # Store gradient client for later tool binding
        self._gradient_client = gradient_client

        # For now, return a mock LangChain LLM (will be replaced with actual LLM at runtime)
        # This avoids requiring API keys at import/initialization time
        try:
            # Try to get LangChain LLM if client is configured
            if gradient_client.is_enabled():
                return gradient_client.get_llm_with_tools(
                    tools=[],
                    temperature=agent_config.get("temperature", 0.7),
                    max_tokens=agent_config.get("max_tokens", 2000),
                )
        except:
            pass

        # Return gradient client itself (has invoke/ainvoke methods)
        return gradient_client

    def _bind_tools(self) -> BaseChatModel | Any:
        """Bind MCP tools to LLM for function calling.

        Uses progressive tool disclosure to reduce token usage.
        """
        tools_config = self.config.get("tools", {})

        # Get allowed MCP servers for this agent
        allowed_servers = tools_config.get("allowed_servers", [])

        # Skip tool binding if no MCP client or no servers configured
        if not allowed_servers or not self.mcp_client:
            return self.llm

        # For now, return LLM without tools (tools will be bound at runtime with task context)
        # This avoids import-time dependencies on MCP gateway
        # TODO: Implement runtime tool binding with progressive disclosure
        return self.llm

    def get_system_prompt(self) -> str:
        """Get agent-specific system prompt from system.prompt.md file or YAML config.

        Implements Factor 2 (Own Your Prompts) by loading prompts from version-controlled
        system.prompt.md files in agent directory, with fallback to YAML config for
        backward compatibility.

        Returns:
            System prompt string for LLM initialization
        """
        # Try loading from system.prompt.md in agent directory
        # Path structure: agents/{agent_name}/system.prompt.md
        prompt_file = (
            Path(__file__).parent.parent / self.agent_name / "system.prompt.md"
        )

        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")

        # Fallback to YAML config for backward compatibility
        return self.config["agent"].get(
            "system_prompt", "You are a helpful AI assistant."
        )

    @traceable(name="agent_invoke", tags=["agent", "subagent"])
    async def invoke(
        self, messages: List[BaseMessage], config: Optional[RunnableConfig] = None
    ) -> BaseMessage:
        """Execute agent with given messages.

        Args:
            messages: List of messages (conversation history + current task)
            config: Optional runnable configuration (for LangGraph tracing)

        Returns:
            Agent's response message

        Note: Decorated with @traceable to capture in LangSmith as nested runs.
        The agent_name is added as metadata for filtering in traces.
        """
        # Prepend system prompt if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=self.get_system_prompt())] + messages

        # Execute LLM with bound tools
        response = await self.agent_executor.ainvoke(messages, config=config)

        return response

    def __repr__(self) -> str:
        """String representation of agent."""
        model = self.config["agent"].get("model", "unknown")
        return f"<{self.__class__.__name__} agent={self.agent_name} model={model}>"

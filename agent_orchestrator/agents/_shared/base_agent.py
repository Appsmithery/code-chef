"""Base agent class for LangGraph agent nodes."""

import sys
import yaml
import hashlib
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
    4. Binds tools dynamically at invoke-time (not init-time) for token efficiency
    5. Provides invoke() method for graph execution

    Tool Binding Strategy (per architecture decision):
    - Tools are bound at invoke-time based on task context
    - Progressive tool loading reduces tokens from 150+ to 10-30 per request
    - Bound LLM instances are cached by tool configuration hash
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

        # Initialize LLM with agent-specific model (without tools - bound at invoke time)
        self.llm = self._initialize_llm()

        # Cache for bound LLM instances (key: tool config hash)
        self._bound_llm_cache: Dict[str, BaseChatModel] = {}

        # Legacy: agent_executor points to base LLM (tools bound dynamically)
        self.agent_executor = self.llm

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
        """Legacy method - returns base LLM without tools.

        Tools are now bound dynamically at invoke-time via _bind_tools_for_task().
        This method exists for backward compatibility.
        """
        return self.llm

    def _get_cache_key(self, tools: List[Any]) -> str:
        """Create stable cache key from tool list.

        Args:
            tools: List of tool objects with .name attribute

        Returns:
            MD5 hash (first 16 chars) of sorted tool names
        """
        tool_names = sorted([getattr(t, "name", str(t)) for t in tools])
        tool_str = ",".join(tool_names)
        return hashlib.md5(tool_str.encode()).hexdigest()[:16]

    async def _bind_tools_for_task(self, task_description: str) -> BaseChatModel | Any:
        """Bind tools dynamically based on task context.

        Uses progressive tool disclosure to select only relevant tools,
        reducing token usage from 150+ to 10-30 tools per request.

        Args:
            task_description: Natural language description of the task

        Returns:
            LLM with appropriate tools bound for the task
        """
        if not self.tool_loader:
            logger.debug(f"[{self.agent_name}] No tool loader, using base LLM")
            return self.llm

        tools_config = self.config.get("tools", {})

        try:
            # Get progressive strategy from config
            strategy_name = tools_config.get("progressive_strategy", "MINIMAL")
            strategy = ToolLoadingStrategy[strategy_name]

            # Get allowed servers for this agent
            allowed_servers = tools_config.get("allowed_servers", [])

            # Load relevant tools via progressive disclosure
            tools = await self.tool_loader.load_tools_for_task(
                task_description=task_description,
                strategy=strategy,
                allowed_servers=allowed_servers if allowed_servers else None,
            )

            if not tools:
                logger.debug(f"[{self.agent_name}] No tools matched, using base LLM")
                return self.llm

            # Check cache for this tool configuration
            cache_key = self._get_cache_key(tools)
            if cache_key in self._bound_llm_cache:
                logger.debug(
                    f"[{self.agent_name}] Using cached LLM for tools: {cache_key}"
                )
                return self._bound_llm_cache[cache_key]

            # Bind tools and cache result
            agent_config = self.config.get("agent", {})
            bound_llm = self._gradient_client.get_llm_with_tools(
                tools=tools,
                temperature=agent_config.get("temperature", 0.7),
                max_tokens=agent_config.get("max_tokens", 2000),
            )

            self._bound_llm_cache[cache_key] = bound_llm
            logger.info(
                f"[{self.agent_name}] Bound {len(tools)} tools for task. "
                f"Cache key: {cache_key}"
            )

            return bound_llm

        except Exception as e:
            logger.warning(
                f"[{self.agent_name}] Tool binding failed: {e}, using base LLM"
            )
            return self.llm

    def _extract_task_description(self, messages: List[BaseMessage]) -> str:
        """Extract task description from most recent HumanMessage.

        Args:
            messages: List of conversation messages

        Returns:
            Task description (max 500 chars) for tool matching
        """
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content[:500]  # Limit for tool matching efficiency
        return ""

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
        """Execute agent with given messages and dynamically bound tools.

        Args:
            messages: List of messages (conversation history + current task)
            config: Optional runnable configuration (for LangGraph tracing)

        Returns:
            Agent's response message

        Tool Binding (per architecture decision):
        - Extracts task description from messages
        - Binds only relevant tools via progressive disclosure
        - Caches bound LLM by tool configuration hash

        Note: Decorated with @traceable to capture in LangSmith as nested runs.
        The agent_name is added as metadata for filtering in traces.
        """
        # Extract task description for tool selection
        task_description = self._extract_task_description(messages)

        # Bind tools dynamically based on task context
        executor = await self._bind_tools_for_task(task_description)

        # Prepend system prompt if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=self.get_system_prompt())] + messages

        # Execute LLM with dynamically bound tools
        logger.debug(f"[{self.agent_name}] Invoking with {len(messages)} messages")
        response = await executor.ainvoke(messages, config=config)

        return response

    def __repr__(self) -> str:
        """String representation of agent."""
        model = self.config["agent"].get("model", "unknown")
        return f"<{self.__class__.__name__} agent={self.agent_name} model={model}>"

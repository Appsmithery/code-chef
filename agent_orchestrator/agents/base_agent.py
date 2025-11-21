"""Base agent class for LangGraph agent nodes."""

import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from lib.mcp_client import MCPClient
from lib.gradient_client import get_gradient_client
from lib.progressive_mcp_loader import ProgressiveMCPLoader, ToolLoadingStrategy


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
        
        # Initialize progressive tool loader
        self.tool_loader = ProgressiveMCPLoader(self.mcp_client)
        
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
          project: agents-feature-dev
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
    
    def _initialize_llm(self) -> BaseChatModel:
        """Initialize LLM with agent-specific configuration."""
        agent_config = self.config["agent"]
        
        # Get Gradient client with agent-specific model
        llm = get_gradient_client(
            model_name=agent_config.get("model", "llama-3.1-8b"),
            temperature=agent_config.get("temperature", 0.7),
            max_tokens=agent_config.get("max_tokens", 2000),
            agent_name=self.agent_name
        )
        
        return llm
    
    def _bind_tools(self) -> BaseChatModel:
        """Bind MCP tools to LLM for function calling.
        
        Uses progressive tool disclosure to reduce token usage.
        """
        tools_config = self.config["tools"]
        
        # Get progressive loading strategy
        strategy_name = tools_config.get("progressive_strategy", "MINIMAL")
        strategy = ToolLoadingStrategy[strategy_name]
        
        # Get allowed MCP servers for this agent
        allowed_servers = tools_config.get("allowed_servers", [])
        
        # Load tools with progressive disclosure
        # Note: For initialization, we load tools without task context
        # At runtime, call get_tools_for_task() with actual task description
        langchain_tools = self.mcp_client.to_langchain_tools(allowed_servers)
        
        # Bind tools to LLM
        return self.llm.bind_tools(langchain_tools)
    
    def get_system_prompt(self) -> str:
        """Get agent-specific system prompt from configuration."""
        return self.config["agent"].get("system_prompt", "You are a helpful AI assistant.")
    
    async def invoke(
        self,
        messages: List[BaseMessage],
        config: Optional[RunnableConfig] = None
    ) -> BaseMessage:
        """Execute agent with given messages.
        
        Args:
            messages: List of messages (conversation history + current task)
            config: Optional runnable configuration (for LangGraph tracing)
        
        Returns:
            Agent's response message
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

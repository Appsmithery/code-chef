"""Base agent class for LangGraph agent nodes.

Provides:
1. LLM initialization with agent-specific configuration
2. Progressive tool loading for token-efficient tool binding
3. Cross-agent memory for knowledge sharing
4. **Inter-agent communication via EventBus** (Phase 6 - CHEF-110)

Inter-Agent Communication:
    Agents can request work from other agents using the EventBus pub/sub pattern:
    
    # Request help from code-review agent
    response = await self.request_agent(
        target_agent="code-review",
        request_type=AgentRequestType.REVIEW_CODE,
        payload={"file_path": "main.py"}
    )
    
    # Broadcast status to all agents
    await self.broadcast_status("task_completed", {"task_id": "123"})
"""

import os
import sys
import yaml
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langsmith import traceable

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from lib.mcp_client import MCPClient
from lib.gradient_client import get_gradient_client
from lib.progressive_mcp_loader import ProgressiveMCPLoader, ToolLoadingStrategy

# Inter-agent communication (Phase 6 - CHEF-110)
from lib.event_bus import EventBus, Event
from lib.agent_events import (
    AgentRequestEvent,
    AgentResponseEvent,
    AgentRequestType,
    AgentResponseStatus,
    AgentRequestPriority,
    AgentBroadcastEvent,
)

# Agent memory for cross-agent knowledge sharing
try:
    from lib.agent_memory import AgentMemoryManager, InsightType, Insight

    MEMORY_ENABLED = True
except ImportError:
    MEMORY_ENABLED = False
    AgentMemoryManager = None
    InsightType = None
    Insight = None

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

        # Initialize agent memory for cross-agent knowledge sharing
        self.memory_manager: Optional[AgentMemoryManager] = None
        self._memory_enabled = False
        if MEMORY_ENABLED:
            try:
                memory_config = self.config.get("memory", {})
                if memory_config.get("enabled", True):
                    self.memory_manager = AgentMemoryManager(agent_id=agent_name)
                    self._memory_enabled = True
                    logger.info(
                        f"[{agent_name}] Agent memory enabled for cross-agent knowledge sharing"
                    )
            except Exception as e:
                logger.warning(
                    f"[{agent_name}] Agent memory initialization failed: {e}"
                )

        # Initialize LLM with agent-specific model (without tools - bound at invoke time)
        self.llm = self._initialize_llm()

        # Cache for bound LLM instances (key: tool config hash)
        self._bound_llm_cache: Dict[str, BaseChatModel] = {}

        # Legacy: agent_executor points to base LLM (tools bound dynamically)
        self.agent_executor = self.llm

        # Inter-agent communication via EventBus (Phase 6 - CHEF-110)
        self._event_bus: Optional[EventBus] = None
        self._event_bus_connected = False

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

    @traceable(name="agent_bind_tools", tags=["agent", "tools", "mcp"])
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

    @traceable(name="agent_retrieve_memory", tags=["agent", "memory", "rag"])
    async def _retrieve_relevant_context(self, task_description: str) -> str:
        """Retrieve relevant insights from agent memory for context injection.

        Queries cross-agent memory for insights relevant to the current task.
        Injects this context into the system prompt to benefit from collective learning.

        Args:
            task_description: Natural language description of the task

        Returns:
            Formatted context string to inject into system prompt (empty if none found)
        """
        if not self._memory_enabled or not self.memory_manager:
            return ""

        try:
            memory_config = self.config.get("memory", {})
            max_insights = memory_config.get("max_context_insights", 3)
            min_confidence = memory_config.get("min_confidence", 0.6)

            # Retrieve relevant insights from cross-agent memory
            insights = await self.memory_manager.retrieve_relevant(
                query=task_description,
                limit=max_insights,
                min_confidence=min_confidence,
            )

            if not insights:
                return ""

            # Format insights for prompt injection
            context_lines = ["\n## Relevant Insights from Prior Agent Work\n"]
            for insight in insights:
                agent_label = (
                    insight.agent_id if insight.agent_id != self.agent_name else "self"
                )
                context_lines.append(
                    f"- **{insight.insight_type}** (from {agent_label}, "
                    f"confidence: {insight.relevance_score:.2f}):\n  {insight.content[:300]}"
                )

            logger.info(
                f"[{self.agent_name}] Injected {len(insights)} insights into context"
            )
            return "\n".join(context_lines)

        except Exception as e:
            logger.warning(f"[{self.agent_name}] Memory retrieval failed: {e}")
            return ""

    @traceable(name="agent_extract_insight", tags=["agent", "memory", "extraction"])
    async def _extract_and_store_insights(
        self,
        task_description: str,
        response: BaseMessage,
        workflow_id: Optional[str] = None,
    ) -> None:
        """Extract actionable insights from agent response and store in memory.

        Uses pattern detection to identify insights worth sharing:
        - Architectural decisions (design choices, patterns used)
        - Error patterns (how issues were diagnosed/resolved)
        - Code patterns (reusable implementations)
        - Security findings (vulnerabilities, mitigations)

        Args:
            task_description: Original task description
            response: Agent's response message
            workflow_id: Optional workflow ID for tracing
        """
        if not self._memory_enabled or not self.memory_manager:
            return

        try:
            memory_config = self.config.get("memory", {})
            if not memory_config.get("extract_insights", True):
                return

            response_content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Simple pattern-based insight detection
            # In production, this could use an LLM for more sophisticated extraction
            insights_to_store = self._detect_insights(
                task_description, response_content
            )

            for insight_type, content in insights_to_store:
                await self.memory_manager.store_insight(
                    insight_type=insight_type,
                    content=content,
                    source_task=task_description[:200],
                    source_workflow_id=workflow_id,
                    metadata={
                        "agent_name": self.agent_name,
                        "response_length": len(response_content),
                    },
                )

            if insights_to_store:
                logger.info(
                    f"[{self.agent_name}] Stored {len(insights_to_store)} insights to memory"
                )

        except Exception as e:
            logger.warning(f"[{self.agent_name}] Insight extraction failed: {e}")

    def _detect_insights(
        self, task_description: str, response_content: str
    ) -> List[tuple]:
        """Detect extractable insights from response using pattern matching.

        This is a lightweight heuristic approach. For production, consider:
        - LLM-based extraction with structured output
        - Confidence scoring based on response quality
        - Deduplication against existing insights

        Args:
            task_description: Original task description
            response_content: Agent's response text

        Returns:
            List of (InsightType, content) tuples
        """
        insights = []
        response_lower = response_content.lower()

        # Only extract insights from substantive responses
        if len(response_content) < 100:
            return insights

        # Detect error patterns
        error_keywords = [
            "fixed",
            "resolved",
            "bug",
            "error",
            "exception",
            "traceback",
            "debugging",
        ]
        if any(kw in response_lower for kw in error_keywords):
            # Extract the resolution paragraph
            for para in response_content.split("\n\n"):
                if any(
                    kw in para.lower()
                    for kw in ["fix", "solution", "resolved", "the issue"]
                ):
                    insights.append((InsightType.ERROR_PATTERN, para[:500]))
                    break

        # Detect architectural decisions
        arch_keywords = [
            "architecture",
            "design pattern",
            "structure",
            "approach",
            "decision",
        ]
        if any(kw in response_lower for kw in arch_keywords):
            for para in response_content.split("\n\n"):
                if any(
                    kw in para.lower()
                    for kw in ["chose", "decided", "approach", "pattern", "structure"]
                ):
                    insights.append((InsightType.ARCHITECTURAL_DECISION, para[:500]))
                    break

        # Detect security findings
        security_keywords = [
            "security",
            "vulnerability",
            "authentication",
            "authorization",
            "injection",
            "xss",
        ]
        if any(kw in response_lower for kw in security_keywords):
            for para in response_content.split("\n\n"):
                if any(kw in para.lower() for kw in security_keywords):
                    insights.append((InsightType.SECURITY_FINDING, para[:500]))
                    break

        # Detect code patterns (only for feature_dev and code_review agents)
        if self.agent_name in ["feature_dev", "code_review"]:
            code_keywords = ["implementation", "function", "class", "method", "pattern"]
            if (
                any(kw in response_lower for kw in code_keywords)
                and "```" in response_content
            ):
                # Extract code block context
                code_start = response_content.find("```")
                code_end = response_content.find("```", code_start + 3)
                if code_end > code_start:
                    code_block = response_content[code_start : code_end + 3]
                    if len(code_block) > 50:
                        insights.append((InsightType.CODE_PATTERN, code_block[:800]))

        return insights

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

        Knowledge Sharing (cross-agent memory):
        - Retrieves relevant insights from prior agent work
        - Extracts actionable insights from response for future agents
        - Stores insights with workflow context for traceability

        Note: Decorated with @traceable to capture in LangSmith as nested runs.
        The agent_name is added as metadata for filtering in traces.
        """
        # Extract task description for tool selection and memory queries
        task_description = self._extract_task_description(messages)

        # Bind tools dynamically based on task context
        executor = await self._bind_tools_for_task(task_description)

        # Retrieve relevant context from cross-agent memory
        memory_context = await self._retrieve_relevant_context(task_description)

        # Build system prompt with optional memory context
        system_prompt = self.get_system_prompt()
        if memory_context:
            system_prompt = f"{system_prompt}\n{memory_context}"

        # Prepend system prompt if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + messages
        else:
            # Update existing system message with memory context
            if memory_context:
                messages = [
                    SystemMessage(content=f"{messages[0].content}\n{memory_context}")
                ] + messages[1:]

        # Execute LLM with dynamically bound tools
        logger.debug(f"[{self.agent_name}] Invoking with {len(messages)} messages")
        response = await executor.ainvoke(messages, config=config)

        # Extract and store insights from response for cross-agent learning
        workflow_id = None
        if config and config.get("configurable"):
            workflow_id = config["configurable"].get("thread_id")

        await self._extract_and_store_insights(task_description, response, workflow_id)

        return response

    # =========================================================================
    # INTER-AGENT COMMUNICATION (Phase 6 - CHEF-110)
    # =========================================================================

    async def _get_event_bus(self) -> EventBus:
        """Get or initialize the EventBus singleton.

        Lazily connects to EventBus on first use to avoid issues with
        async initialization during class instantiation.

        Returns:
            Connected EventBus instance
        """
        if self._event_bus is None:
            self._event_bus = EventBus.get_instance()

        if not self._event_bus_connected:
            try:
                await self._event_bus.connect()
                self._event_bus_connected = True
                logger.debug(f"[{self.agent_name}] Connected to EventBus")
            except Exception as e:
                logger.warning(f"[{self.agent_name}] EventBus connection failed: {e}")

        return self._event_bus

    @traceable(name="agent_request_agent", tags=["agent", "inter-agent", "request"])
    async def request_agent(
        self,
        target_agent: str,
        request_type: AgentRequestType,
        payload: Dict[str, Any],
        priority: AgentRequestPriority = AgentRequestPriority.NORMAL,
        timeout: float = 30.0,
        correlation_id: Optional[str] = None,
    ) -> AgentResponseEvent:
        """Request work from another agent via EventBus.

        Implements agent-to-agent communication for Phase 6 multi-agent workflows.
        The request is routed through EventBus pub/sub, with optional Redis
        for cross-process communication.

        Args:
            target_agent: Name of the agent to request (e.g., "code-review")
            request_type: Type of request from AgentRequestType enum
            payload: Request-specific data (file paths, code, context)
            priority: Request priority level (affects queue ordering)
            timeout: Maximum seconds to wait for response
            correlation_id: Optional ID for grouping related requests

        Returns:
            AgentResponseEvent with result or error

        Example:
            # Request code review from code-review agent
            response = await self.request_agent(
                target_agent="code-review",
                request_type=AgentRequestType.REVIEW_CODE,
                payload={"file_path": "main.py", "changes": diff_content}
            )

            if response.status == AgentResponseStatus.SUCCESS:
                review_comments = response.result["comments"]
            else:
                logger.error(f"Review failed: {response.error}")
        """
        event_bus = await self._get_event_bus()

        # Create request event
        request = AgentRequestEvent(
            source_agent=self.agent_name,
            target_agent=target_agent,
            request_type=request_type,
            payload=payload,
            priority=priority,
            timeout_seconds=timeout,
            correlation_id=correlation_id,
            metadata={
                "source_model": self.config.get("agent", {}).get("model", "unknown"),
            },
        )

        logger.info(
            f"[{self.agent_name}] Requesting {request_type.value} from {target_agent} "
            f"(request_id: {request.request_id})"
        )

        # Send request and await response
        response = await event_bus.request_agent(request, timeout=timeout)

        logger.info(
            f"[{self.agent_name}] Received response from {response.source_agent} "
            f"(status: {response.status.value}, time: {response.processing_time_ms}ms)"
        )

        return response

    @traceable(name="agent_respond_to_request", tags=["agent", "inter-agent", "response"])
    async def respond_to_request(
        self,
        request: AgentRequestEvent,
        status: AgentResponseStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        processing_time_ms: Optional[float] = None,
    ) -> None:
        """Send response to an agent request via EventBus.

        Called by agents when they complete processing of an AgentRequestEvent.
        The response is correlated to the original request by request_id.

        Args:
            request: Original AgentRequestEvent being responded to
            status: Response status (SUCCESS, ERROR, TIMEOUT, REJECTED)
            result: Response data (for SUCCESS or PARTIAL status)
            error: Error message (for ERROR or TIMEOUT status)
            processing_time_ms: Time taken to process request
        """
        event_bus = await self._get_event_bus()

        response = AgentResponseEvent(
            request_id=request.request_id,
            source_agent=self.agent_name,
            target_agent=request.source_agent,
            status=status,
            result=result,
            error=error,
            processing_time_ms=processing_time_ms,
            metadata={
                "responder_model": self.config.get("agent", {}).get("model", "unknown"),
            },
        )

        await event_bus.respond_to_request(response)

        logger.info(
            f"[{self.agent_name}] Sent response to {request.source_agent} "
            f"(request_id: {request.request_id}, status: {status.value})"
        )

    @traceable(name="agent_broadcast_status", tags=["agent", "inter-agent", "broadcast"])
    async def broadcast_status(
        self,
        event_type: str,
        payload: Dict[str, Any],
        target_agents: Optional[List[str]] = None,
        priority: AgentRequestPriority = AgentRequestPriority.NORMAL,
    ) -> None:
        """Broadcast status update to other agents via EventBus.

        Use for notifications, state changes, or announcements that
        multiple agents should be aware of (e.g., task completion,
        resource locking, workflow checkpoints).

        Args:
            event_type: Type of broadcast (e.g., "task_completed", "resource_locked")
            payload: Event data
            target_agents: List of agent names, or None for all agents
            priority: Broadcast priority level

        Example:
            # Notify all agents that a task is complete
            await self.broadcast_status(
                event_type="task_completed",
                payload={"task_id": "123", "result": "success"}
            )

            # Notify specific agents about resource lock
            await self.broadcast_status(
                event_type="resource_locked",
                payload={"resource": "deployment:production"},
                target_agents=["infrastructure", "cicd"]
            )
        """
        event_bus = await self._get_event_bus()

        broadcast = AgentBroadcastEvent(
            source_agent=self.agent_name,
            target_agents=target_agents or ["all"],
            event_type=event_type,
            payload=payload,
            priority=priority,
        )

        await event_bus.emit(
            event_type=event_type,
            data=broadcast.to_dict(),
            source=self.agent_name,
            correlation_id=broadcast.broadcast_id,
        )

        target_str = ", ".join(broadcast.target_agents)
        logger.info(
            f"[{self.agent_name}] Broadcast {event_type} to {target_str} "
            f"(broadcast_id: {broadcast.broadcast_id})"
        )

    @traceable(name="agent_subscribe_to_events", tags=["agent", "inter-agent", "subscribe"])
    async def subscribe_to_events(
        self,
        event_types: List[str],
        handler: Any,  # Callable[[Event], Any]
    ) -> None:
        """Subscribe to events from other agents.

        Registers a callback handler for specified event types. The handler
        is called asynchronously when matching events are emitted.

        Args:
            event_types: List of event types to subscribe to
            handler: Async callback function with signature (Event) -> None

        Example:
            async def handle_task_completed(event: Event):
                task_id = event.data["task_id"]
                logger.info(f"Task {task_id} completed by {event.source}")

            await self.subscribe_to_events(
                event_types=["task_completed"],
                handler=handle_task_completed
            )
        """
        event_bus = await self._get_event_bus()

        for event_type in event_types:
            event_bus.subscribe(event_type, handler)
            logger.debug(f"[{self.agent_name}] Subscribed to {event_type}")

        logger.info(
            f"[{self.agent_name}] Subscribed to {len(event_types)} event types"
        )

    def __repr__(self) -> str:
        """String representation of agent."""
        model = self.config["agent"].get("model", "unknown")
        return f"<{self.__class__.__name__} agent={self.agent_name} model={model}>"

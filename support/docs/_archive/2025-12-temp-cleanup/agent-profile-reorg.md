# **Agent Profile Reorganization Plan**

## Current Structure Issues

### 1. **Confusing Separation**

**Current:**
```
agent_orchestrator/
├── agents/           # Python agent implementations
│   ├── supervisor.py
│   ├── feature_dev.py
│   └── ...
├── prompts/          # System prompts
│   ├── supervisor.prompt.md
│   ├── feature-dev.prompt.md
│   └── tools/        # ⚠️ Tool USAGE GUIDES (how to call tools)
│       ├── git-tools.prompt.md
│       └── docker-tools.prompt.md
├── tools/            # ⚠️ Tool CONFIGURATION (which tools to load)
│   ├── supervisor_tools.yaml
│   └── feature_dev_tools.yaml
└── workflows/
```

**The Confusion:**
- `agent_orchestrator/tools/*.yaml` = **"Which MCP tools should this agent have access to?"** (configuration)
- `agent_orchestrator/prompts/tools/*.prompt.md` = **"How should the agent USE these tools?"** (documentation/examples)

This separation makes sense because:
- **Tool configs** (`tools/*.yaml`) are **agent-specific** - supervisor needs different tools than feature-dev
- **Tool prompts** (`prompts/tools/*.prompt.md`) are **cross-cutting** - multiple agents use git tools the same way

### 2. **But You're Right About Agent-Centric Organization**

A better structure groups by agent profile:

## Proposed Structure: Agent-Centric

```
agent_orchestrator/
├── agents/
│   ├── supervisor/
│   │   ├── __init__.py              # Agent implementation (Python)
│   │   ├── system.prompt.md         # System prompt (role, routing rules)
│   │   ├── tools.yaml               # Tool access list (MCP servers)
│   │   └── workflows/               # Agent-specific workflows
│   │       └── task-decomposition.workflow.yaml
│   │
│   ├── feature_dev/
│   │   ├── __init__.py
│   │   ├── system.prompt.md         # Code generation prompt
│   │   ├── tools.yaml               # filesystem, git, github tools
│   │   └── workflows/
│   │       ├── implement-feature.workflow.yaml
│   │       └── refactor-code.workflow.yaml
│   │
│   ├── code_review/
│   │   ├── __init__.py
│   │   ├── system.prompt.md         # Security/quality analysis prompt
│   │   ├── tools.yaml               # git, github, semgrep tools
│   │   └── workflows/
│   │       └── security-scan.workflow.yaml
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── system.prompt.md         # IaC generation prompt
│   │   ├── tools.yaml               # docker, terraform, kubectl tools
│   │   └── workflows/
│   │       ├── deploy-staging.workflow.yaml
│   │       └── rollback-production.workflow.yaml
│   │
│   ├── cicd/
│   │   ├── __init__.py
│   │   ├── system.prompt.md         # Pipeline automation prompt
│   │   ├── tools.yaml               # github actions, jenkins tools
│   │   └── workflows/
│   │       └── create-pipeline.workflow.yaml
│   │
│   ├── documentation/
│   │   ├── __init__.py
│   │   ├── system.prompt.md         # Technical writing prompt
│   │   ├── tools.yaml               # notion, filesystem tools
│   │   └── workflows/
│   │       └── generate-docs.workflow.yaml
│   │
│   └── _shared/                     # Cross-cutting tool documentation
│       ├── base_agent.py            # BaseAgent class
│       └── tool_guides/             # Tool USAGE guides (shared)
│           ├── git-tools.prompt.md
│           ├── docker-tools.prompt.md
│           ├── linear-tools.prompt.md
│           └── notion-tools.prompt.md
│
├── workflows/
│   ├── templates/                   # Multi-agent workflows
│   │   ├── pr-deployment.workflow.yaml
│   │   ├── hotfix.workflow.yaml
│   │   └── feature-pipeline.workflow.yaml
│   ├── engine.py                    # WorkflowEngine class
│   └── reducers.py                  # State management
│
└── graph.py                         # LangGraph StateGraph definition
```

## Benefits of Agent-Centric Structure

### 1. **Locality of Behavior**
Everything for an agent in one place:
```python
# Before: scattered across 3 directories
agent_orchestrator/agents/feature_dev.py
agent_orchestrator/prompts/feature-dev.prompt.md
agent_orchestrator/tools/feature_dev_tools.yaml

# After: single directory
agent_orchestrator/agents/feature_dev/__init__.py
agent_orchestrator/agents/feature_dev/system.prompt.md
agent_orchestrator/agents/feature_dev/tools.yaml
```

### 2. **Easier Onboarding**
New developers can understand an agent by exploring ONE directory, not hunting across multiple folders.

### 3. **Agent-Specific Workflows**
Each agent can have its own workflow templates:
```yaml
# agent_orchestrator/agents/infrastructure/workflows/deploy-staging.workflow.yaml
name: "Deploy to Staging"
agent: "infrastructure"
steps:
  - id: "build_image"
    type: "tool_call"
    tool: "docker.build"
  - id: "push_image"
    type: "tool_call"
    tool: "dockerhub.push"
  - id: "deploy_k8s"
    type: "tool_call"
    tool: "kubectl.apply"
```

### 4. **Shared Tool Guides Remain DRY**
Tool usage guides (`git-tools.prompt.md`) stay in `_shared/tool_guides/` since they're used by multiple agents.

## Migration Plan

````bash
#!/bin/bash
set -e

echo "🔄 Reorganizing agent structure to agent-centric layout..."

# Create new agent directories
for agent in supervisor feature_dev code_review infrastructure cicd documentation; do
    mkdir -p "agent_orchestrator/agents/${agent}/workflows"
    echo "✅ Created agent_orchestrator/agents/${agent}/"
done

# Create shared directory
mkdir -p "agent_orchestrator/agents/_shared/tool_guides"

# Move agent implementations
for agent in supervisor feature_dev code_review infrastructure cicd documentation; do
    # Convert kebab-case to snake_case for file names
    file_name=$(echo "$agent" | sed 's/-/_/g')
    
    if [ -f "agent_orchestrator/agents/${file_name}.py" ]; then
        mv "agent_orchestrator/agents/${file_name}.py" \
           "agent_orchestrator/agents/${agent}/__init__.py"
        echo "✅ Moved ${file_name}.py → ${agent}/__init__.py"
    fi
done

# Move system prompts
for agent in supervisor feature-dev code-review infrastructure cicd documentation; do
    # Convert to directory name (snake_case)
    dir_name=$(echo "$agent" | sed 's/-/_/g')
    
    if [ -f "agent_orchestrator/prompts/${agent}.prompt.md" ]; then
        mv "agent_orchestrator/prompts/${agent}.prompt.md" \
           "agent_orchestrator/agents/${dir_name}/system.prompt.md"
        echo "✅ Moved ${agent}.prompt.md → ${dir_name}/system.prompt.md"
    fi
done

# Move tool configs
for agent in supervisor feature_dev code_review infrastructure cicd documentation; do
    if [ -f "agent_orchestrator/tools/${agent}_tools.yaml" ]; then
        mv "agent_orchestrator/tools/${agent}_tools.yaml" \
           "agent_orchestrator/agents/${agent}/tools.yaml"
        echo "✅ Moved ${agent}_tools.yaml → ${agent}/tools.yaml"
    fi
done

# Move shared tool guides
if [ -d "agent_orchestrator/prompts/tools" ]; then
    mv agent_orchestrator/prompts/tools/* \
       agent_orchestrator/agents/_shared/tool_guides/
    echo "✅ Moved tool guides to _shared/tool_guides/"
fi

# Move base_agent.py to _shared
if [ -f "agent_orchestrator/agents/base_agent.py" ]; then
    mv "agent_orchestrator/agents/base_agent.py" \
       "agent_orchestrator/agents/_shared/base_agent.py"
    echo "✅ Moved base_agent.py to _shared/"
fi

# Clean up old directories
rm -rf agent_orchestrator/prompts
rm -rf agent_orchestrator/tools
echo "✅ Removed old prompts/ and tools/ directories"

# Update imports in graph.py
echo "⚠️  TODO: Update imports in graph.py:"
echo "  from agents.supervisor import supervisor_node"
echo "  →"
echo "  from agents.supervisor import supervisor_node"

echo ""
echo "🎉 Agent reorganization complete!"
echo ""
echo "Next steps:"
echo "  1. Update import paths in graph.py and workflows/"
echo "  2. Update BaseAgent.get_system_prompt() path:"
echo "     agent_orchestrator/agents/{agent_name}/system.prompt.md"
echo "  3. Update tool config paths:"
echo "     agent_orchestrator/agents/{agent_name}/tools.yaml"
echo "  4. Test: python -m agent_orchestrator.main"
````

## Updated BaseAgent Implementation

````python
"""Base agent class for LangGraph agent nodes."""

import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from lib.mcp_client import MCPClient
from lib.gradient_client import get_gradient_client
from lib.progressive_mcp_loader import ProgressiveMCPLoader, ToolLoadingStrategy

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for LangGraph agent nodes.

    Each agent node:
    1. Loads configuration from agent directory (system.prompt.md, tools.yaml)
    2. Initializes MCP client for tool access
    3. Initializes LLM with model-specific settings
    4. Binds tools to LLM for function calling
    5. Provides invoke() method for graph execution
    """

    def __init__(self, agent_name: str):
        """Initialize agent with name (auto-discovers config files)
        
        Args:
            agent_name: Agent identifier (e.g., 'supervisor', 'feature_dev')
        """
        self.agent_name = agent_name
        self.agent_dir = Path(__file__).parent.parent / agent_name
        
        # Load configuration from agent directory
        self.config = self._load_config()
        self.system_prompt = self._load_system_prompt()
        
        # Initialize clients
        self.mcp_client = MCPClient()
        self.progressive_loader = ProgressiveMCPLoader(self.mcp_client)
        
        # Initialize LLM (if agent uses one)
        if self.config.get("model"):
            self.llm = self._initialize_llm()
            self.llm_with_tools = None  # Lazy-loaded when tools bound

    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration from tools.yaml"""
        config_path = self.agent_dir / "tools.yaml"
        
        if not config_path.exists():
            logger.warning(f"No tools.yaml found for {self.agent_name}, using defaults")
            return {"model": "llama3.3-70b-instruct", "tools": []}
        
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _load_system_prompt(self) -> str:
        """Load system prompt from system.prompt.md (Factor 2: Own Your Prompts)"""
        prompt_path = self.agent_dir / "system.prompt.md"
        
        if prompt_path.exists():
            return prompt_path.read_text()
        
        # Fallback to config if no prompt file
        logger.warning(f"No system.prompt.md for {self.agent_name}, using config fallback")
        return self.config.get("system_prompt", "You are a helpful AI assistant.")

    def _initialize_llm(self) -> BaseChatModel:
        """Initialize Gradient AI LLM with model-specific settings"""
        model_name = self.config["model"]
        
        return get_gradient_client(
            agent_name=self.agent_name,
            model=model_name,
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 2000)
        )

    def _bind_tools(self, task_description: str = "") -> BaseChatModel:
        """Bind MCP tools to LLM for function calling (Factor 4: Tools = JSON)
        
        Args:
            task_description: Current task (for progressive disclosure)
        
        Returns:
            LLM with tools bound via bind_tools()
        """
        # Get relevant tools via progressive disclosure
        toolsets = self.progressive_loader.get_tools_for_task(
            task_description=task_description,
            strategy=ToolLoadingStrategy.PROGRESSIVE,
            agent_manifest_filter=self.agent_name
        )
        
        # Convert to LangChain tools
        langchain_tools = self.mcp_client.to_langchain_tools(toolsets)
        
        # Bind to LLM
        self.llm_with_tools = self.llm.bind_tools(langchain_tools)
        return self.llm_with_tools

    async def invoke(
        self,
        messages: List[BaseMessage],
        config: Optional[RunnableConfig] = None,
        task_description: str = ""
    ) -> BaseMessage:
        """Execute agent node with tool calling
        
        Args:
            messages: Conversation history
            config: LangChain config (for tracing)
            task_description: Current task (for tool selection)
        
        Returns:
            Agent response (may include tool_calls)
        """
        # Bind tools if not already bound
        if not self.llm_with_tools:
            self._bind_tools(task_description)
        
        # Add system prompt
        full_messages = [SystemMessage(content=self.system_prompt)] + messages
        
        # Invoke LLM with tools
        response = await self.llm_with_tools.ainvoke(full_messages, config=config)
        
        return response
````

## Recommendation

**Yes, reorganize by agent profile.** The current file-type separation creates unnecessary cognitive overhead. Here's why:

1. **Agent-centric = behavior-centric**: Everything an agent needs is in one place
2. **Tool configs ARE agent-specific**: `supervisor_tools.yaml` vs `feature_dev_tools.yaml` already proves this
3. **Tool guides are cross-cutting**: Keep in `_shared/tool_guides/` for DRY
4. **Workflows become discoverable**: Each agent's workflows live with the agent

**Exceptions to keep separate:**
- `_shared/tool_guides/` - Used by multiple agents (git, docker, linear)
- `workflows/templates/` - Multi-agent orchestrated workflows (pr-deployment, hotfix)
- `graph.py` - LangGraph definition (references all agents)

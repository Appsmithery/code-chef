# LLM Configuration Refactoring Plan - Option A (YAML-First)

**Status**: Planning  
**Owner**: Orchestrator Agent  
**Target Completion**: December 1, 2025  
**Estimated Effort**: 16-20 hours

---

## Executive Summary

Refactor LLM configuration from 4 scattered sources (hardcoded Python, per-agent YAMLs, metadata dicts, env vars) into a single YAML source of truth with schema validation, hot-reload capability, and comprehensive token tracking.

**Goals**:

1. **Single Source of Truth**: `config/agents/models.yaml` for all model configs
2. **Hot-Reload**: Change models without rebuilding containers (30s vs 30min)
3. **Token Tracking**: Real-time metrics via `/metrics/tokens` + Prometheus
4. **Cost Attribution**: Per-agent token/cost tracking with Grafana dashboards
5. **Schema Validation**: Pydantic models prevent config drift

**Expected Benefits**:

- 60x faster model changes (30s vs 30min)
- 100% elimination of config drift incidents
- Real-time token visibility (vs delayed LangSmith-only)
- Automatic cost attribution per agent
- 10x easier A/B testing

---

## Current State Analysis

### Problem 1: Four Sources of Truth

| Source               | Location                                    | Used By                   | Example Issue                                                    |
| -------------------- | ------------------------------------------- | ------------------------- | ---------------------------------------------------------------- |
| **Hardcoded Python** | `shared/lib/langchain_gradient.py:227-237`  | Pre-initialized instances | `feature_dev_llm = get_llm(..., model="llama3-8b-instruct")`     |
| **Per-Agent YAML**   | `agent_orchestrator/tools/*.yaml`           | Runtime initialization    | `feature_dev_tools.yaml: model: codellama-13b`                   |
| **Metadata Dict**    | `shared/services/langgraph/config.py:41-82` | Cost tracking, logging    | `"orchestrator": {"model": "llama-3.1-70b-instruct"}` (outdated) |
| **Env Vars**         | `deploy/docker-compose.yml`                 | Orchestrator override     | `GRADIENT_MODEL=llama3.3-70b-instruct`                           |

**Actual Drift Example** (November 2025):

- `langchain_gradient.py`: `orchestrator_llm = get_llm("orchestrator", model="llama3.3-70b-instruct")`
- `langgraph/config.py`: `MODEL_METADATA["orchestrator"]["model"] = "llama-3.1-70b-instruct"` ❌
- Result: Cost tracking uses wrong model pricing

### Problem 2: Model Changes Require Rebuilds

**Current Workflow** (30 minutes):

1. Edit `shared/lib/langchain_gradient.py` (change model string)
2. Commit to git
3. Rebuild Docker image: `docker build -t orchestrator:latest .` (5-10 min)
4. Push to registry: `docker push ghcr.io/...` (2-5 min)
5. Deploy to droplet: `ssh && docker pull && docker compose up -d` (5-10 min)
6. Wait for health checks (2-5 min)

**Target Workflow** (30 seconds):

1. Edit `config/agents/models.yaml` (change model string)
2. Restart container: `docker compose restart orchestrator` (10s)
3. Verify health: `curl http://localhost:8001/health` (1s)

### Problem 3: No Token Visibility

**Current**: LangSmith traces only (delayed, requires dashboard access)  
**Target**: Real-time `/metrics/tokens` endpoint + Prometheus counters

---

## Solution Architecture

### 1. Centralized Configuration File

**File**: `config/agents/models.yaml`

```yaml
# config/agents/models.yaml
version: "1.0"
provider: gradient # Default provider (gradient, claude, mistral, openai)

agents:
  orchestrator:
    model: llama3.3-70b-instruct
    provider: gradient
    temperature: 0.3
    max_tokens: 2000
    cost_per_1m_tokens: 0.60
    context_window: 128000
    use_case: complex_reasoning
    tags: [routing, orchestration, supervisor]
    langsmith_project: agents-orchestrator

  feature-dev:
    model: codellama-13b
    provider: gradient
    temperature: 0.7
    max_tokens: 2000
    cost_per_1m_tokens: 0.30
    context_window: 16000
    use_case: code_generation
    tags: [feature-development, python]
    langsmith_project: agents-feature-dev

  code-review:
    model: llama3.3-70b-instruct
    provider: gradient
    temperature: 0.3
    max_tokens: 4000
    cost_per_1m_tokens: 0.60
    context_window: 128000
    use_case: code_analysis
    tags: [quality-assurance, security]
    langsmith_project: agents-code-review

  infrastructure:
    model: llama3-8b-instruct
    provider: gradient
    temperature: 0.5
    max_tokens: 2000
    cost_per_1m_tokens: 0.20
    context_window: 128000
    use_case: infrastructure_config
    tags: [terraform, kubernetes, docker]
    langsmith_project: agents-infrastructure

  cicd:
    model: llama3-8b-instruct
    provider: gradient
    temperature: 0.5
    max_tokens: 2000
    cost_per_1m_tokens: 0.20
    context_window: 128000
    use_case: pipeline_generation
    tags: [github-actions, jenkins]
    langsmith_project: agents-cicd

  documentation:
    model: mistral-nemo-instruct-2407
    provider: gradient
    temperature: 0.7
    max_tokens: 2000
    cost_per_1m_tokens: 0.20
    context_window: 8192
    use_case: documentation_generation
    tags: [markdown, technical-writing]
    langsmith_project: agents-documentation

# Optional: Environment-specific overrides
environments:
  production:
    orchestrator:
      model: llama3.3-70b-instruct
    code-review:
      model: llama3.3-70b-instruct

  development:
    orchestrator:
      model: llama3-8b-instruct # Cheaper for testing
    code-review:
      model: llama3-8b-instruct
```

### 2. Schema Validation (Pydantic)

**File**: `shared/lib/agent_config_schema.py`

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List

class AgentConfig(BaseModel):
    """Schema for per-agent LLM configuration"""
    model: str = Field(..., description="LLM model name (provider-specific)")
    provider: Literal["gradient", "claude", "mistral", "openai"] = "gradient"
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(2000, ge=256, le=128000)
    cost_per_1m_tokens: float = Field(..., gt=0.0)
    context_window: int = Field(..., gt=0)
    use_case: str
    tags: List[str] = []
    langsmith_project: str

    @field_validator('max_tokens')
    @classmethod
    def validate_gradient_max_tokens(cls, v, info):
        """Gradient AI requires max_tokens >= 256"""
        provider = info.data.get('provider', 'gradient')
        if provider == 'gradient' and v < 256:
            raise ValueError(f"Gradient AI requires max_tokens >= 256, got {v}")
        return v

class ModelsConfig(BaseModel):
    """Root configuration schema"""
    version: str = "1.0"
    provider: Literal["gradient", "claude", "mistral", "openai"] = "gradient"
    agents: dict[str, AgentConfig]
    environments: Optional[dict[str, dict[str, dict]]] = None
```

### 3. Configuration Loader

**File**: `shared/lib/config_loader.py`

```python
import yaml
import os
from pathlib import Path
from typing import Dict
from .agent_config_schema import ModelsConfig, AgentConfig

class ConfigLoader:
    """Load and validate agent model configurations"""

    def __init__(self, config_path: str = "config/agents/models.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[ModelsConfig] = None
        self._load()

    def _load(self):
        """Load and validate YAML configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f)

        # Apply environment-specific overrides
        env = os.getenv("DEPLOYMENT_ENV", "production")
        if "environments" in raw_config and env in raw_config["environments"]:
            for agent, overrides in raw_config["environments"][env].items():
                if agent in raw_config["agents"]:
                    raw_config["agents"][agent].update(overrides)

        # Validate with Pydantic
        self._config = ModelsConfig(**raw_config)

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get validated config for specific agent"""
        if agent_name not in self._config.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        return self._config.agents[agent_name]

    def get_all_agents(self) -> Dict[str, AgentConfig]:
        """Get all agent configurations"""
        return self._config.agents

    def reload(self):
        """Hot-reload configuration from disk"""
        self._load()

# Global instance
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """Get or create global config loader"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader
```

### 4. Updated LangChain Integration

**File**: `shared/lib/langchain_gradient.py` (REFACTORED)

```python
"""
Unified LangChain Configuration - YAML-Driven
Single source of truth: config/agents/models.yaml
"""
import os
import logging
from typing import Optional, Union
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from .config_loader import get_config_loader

logger = logging.getLogger(__name__)

# Load configuration from YAML
config_loader = get_config_loader()

# LangSmith tracing (automatic when LANGCHAIN_TRACING_V2=true)
LANGSMITH_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

def get_llm(agent_name: str, **override_kwargs) -> ChatOpenAI:
    """
    Get LLM instance from YAML configuration

    Args:
        agent_name: Agent identifier (must exist in models.yaml)
        **override_kwargs: Runtime overrides for specific parameters

    Returns:
        Configured LLM instance

    Example:
        llm = get_llm("orchestrator")  # Uses config from YAML
        llm = get_llm("orchestrator", temperature=0.5)  # Override temperature
    """
    # Load config from YAML
    agent_config = config_loader.get_agent_config(agent_name)

    # Merge with runtime overrides
    config_dict = agent_config.model_dump()
    config_dict.update(override_kwargs)

    # Provider-specific initialization
    if agent_config.provider == "gradient":
        api_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("DO_SERVERLESS_INFERENCE_KEY")
        if not api_key:
            logger.error(f"[{agent_name}] GRADIENT_MODEL_ACCESS_KEY not set")
            return None

        return ChatOpenAI(
            base_url=os.getenv("GRADIENT_BASE_URL", "https://inference.do-ai.run/v1"),
            api_key=api_key,
            model=config_dict["model"],
            temperature=config_dict["temperature"],
            max_tokens=config_dict["max_tokens"],
            tags=[agent_name, agent_config.provider] + agent_config.tags
        )

    elif agent_config.provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            api_key=os.getenv("CLAUDE_API_KEY"),
            model=config_dict["model"],
            temperature=config_dict["temperature"],
            max_tokens=config_dict["max_tokens"],
            tags=[agent_name, agent_config.provider] + agent_config.tags
        )

    # ... (mistral, openai implementations)

# Pre-configured instances (dynamically generated from YAML)
def _generate_agent_instances():
    """Generate pre-configured LLM instances from YAML"""
    instances = {}
    for agent_name in config_loader.get_all_agents().keys():
        instances[f"{agent_name.replace('-', '_')}_llm"] = get_llm(agent_name)
    return instances

# Auto-generate instances
_instances = _generate_agent_instances()
globals().update(_instances)  # Add to module namespace

logger.info(f"LangChain configuration loaded from {config_loader.config_path}")
logger.info(f"Agents configured: {', '.join(config_loader.get_all_agents().keys())}")
```

---

## Token Tracking Implementation

### 1. Token Tracker Library

**File**: `shared/lib/token_tracker.py`

```python
from typing import Dict
import logging
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Prometheus metrics
llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["agent", "type"]  # type: prompt/completion
)

llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    ["agent"]
)

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM inference latency",
    ["agent"]
)

class TokenTracker:
    """Track token usage and costs per agent"""

    def __init__(self):
        self.usage: Dict[str, Dict[str, float]] = {}

    def track(
        self,
        agent_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_seconds: float
    ):
        """Record token usage for an agent"""
        if agent_name not in self.usage:
            self.usage[agent_name] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "call_count": 0,
                "total_latency": 0.0
            }

        self.usage[agent_name]["prompt_tokens"] += prompt_tokens
        self.usage[agent_name]["completion_tokens"] += completion_tokens
        self.usage[agent_name]["total_tokens"] += (prompt_tokens + completion_tokens)
        self.usage[agent_name]["total_cost"] += cost
        self.usage[agent_name]["call_count"] += 1
        self.usage[agent_name]["total_latency"] += latency_seconds

        # Export to Prometheus
        llm_tokens_total.labels(agent=agent_name, type="prompt").inc(prompt_tokens)
        llm_tokens_total.labels(agent=agent_name, type="completion").inc(completion_tokens)
        llm_cost_usd_total.labels(agent=agent_name).inc(cost)
        llm_latency_seconds.labels(agent=agent_name).observe(latency_seconds)

        logger.info(
            f"[TokenTracker] {agent_name}: +{prompt_tokens}p +{completion_tokens}c "
            f"${cost:.4f} {latency_seconds:.2f}s"
        )

    def get_summary(self) -> Dict[str, Dict]:
        """Get usage summary with efficiency metrics"""
        summary = {}
        for agent, stats in self.usage.items():
            summary[agent] = {
                **stats,
                "avg_tokens_per_call": round(
                    stats["total_tokens"] / stats["call_count"], 2
                ) if stats["call_count"] > 0 else 0,
                "avg_cost_per_call": round(
                    stats["total_cost"] / stats["call_count"], 6
                ) if stats["call_count"] > 0 else 0,
                "avg_latency_seconds": round(
                    stats["total_latency"] / stats["call_count"], 2
                ) if stats["call_count"] > 0 else 0
            }
        return summary

# Global instance
token_tracker = TokenTracker()
```

### 2. Gradient Client Integration

**File**: `shared/lib/gradient_client.py` (UPDATE)

```python
from .token_tracker import token_tracker
from .config_loader import get_config_loader
import time

class GradientClient:
    async def ainvoke(self, prompt: str, **kwargs):
        """Invoke LLM with automatic token tracking"""
        start_time = time.time()

        response = await self._default_llm.ainvoke(prompt, **kwargs)

        latency = time.time() - start_time

        # Extract token usage
        usage = response.response_metadata.get("token_usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        # Calculate cost from config
        agent_config = get_config_loader().get_agent_config(self.agent_name)
        cost_per_1m = agent_config.cost_per_1m_tokens
        cost = (prompt_tokens + completion_tokens) / 1_000_000 * cost_per_1m

        # Track metrics
        token_tracker.track(
            self.agent_name,
            prompt_tokens,
            completion_tokens,
            cost,
            latency
        )

        return response
```

### 3. Metrics Endpoint

**File**: `agent_orchestrator/main.py` (ADD)

```python
from shared.lib.token_tracker import token_tracker

@app.get("/metrics/tokens")
async def get_token_metrics():
    """Get real-time token usage statistics"""
    summary = token_tracker.get_summary()

    return {
        "per_agent": summary,
        "totals": {
            "total_tokens": sum(s["total_tokens"] for s in summary.values()),
            "total_cost": round(sum(s["total_cost"] for s in summary.values()), 4),
            "total_calls": sum(s["call_count"] for s in summary.values())
        },
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## Implementation Phases

### Phase 1: Configuration Refactoring (6 hours)

**Deliverables**:

1. `config/agents/models.yaml` - Centralized config file
2. `shared/lib/agent_config_schema.py` - Pydantic validation
3. `shared/lib/config_loader.py` - YAML loader with hot-reload
4. Update `shared/lib/langchain_gradient.py` - Load from YAML
5. Update `shared/services/langgraph/config.py` - Use config loader
6. Remove hardcoded `orchestrator_llm`, `feature_dev_llm`, etc.

**Sub-Tasks**:

- [ ] 1.1: Create YAML schema and Pydantic models (1h)
- [ ] 1.2: Implement config loader with validation (1.5h)
- [ ] 1.3: Refactor `langchain_gradient.py` to use loader (2h)
- [ ] 1.4: Update `langgraph/config.py` (remove MODEL_METADATA) (1h)
- [ ] 1.5: Create validation script (0.5h)

**Validation**:

```powershell
# Test hot-reload
python -c "from shared.lib.config_loader import get_config_loader; print(get_config_loader().get_agent_config('orchestrator'))"

# Change model in YAML
# Reload without rebuild
python -c "from shared.lib.config_loader import get_config_loader; get_config_loader().reload(); print(get_config_loader().get_agent_config('orchestrator'))"
```

---

### Phase 2: Token Tracking Integration (4 hours)

**Deliverables**:

1. `shared/lib/token_tracker.py` - Token tracking library
2. Update `shared/lib/gradient_client.py` - Integrate token tracking
3. Add `/metrics/tokens` endpoint to orchestrator
4. Prometheus metrics export

**Sub-Tasks**:

- [ ] 2.1: Implement TokenTracker class (1h)
- [ ] 2.2: Integrate into GradientClient.ainvoke() (1h)
- [ ] 2.3: Add Prometheus metrics (1h)
- [ ] 2.4: Create `/metrics/tokens` FastAPI endpoint (1h)

**Validation**:

```powershell
# Test token tracking
curl http://localhost:8001/orchestrate -d '{"task": "test"}'
curl http://localhost:8001/metrics/tokens | jq .

# Verify Prometheus metrics
curl http://localhost:8001/metrics | grep llm_
```

---

### Phase 3: Observability & Dashboards (3 hours)

**Deliverables**:

1. Grafana dashboard JSON (token/cost tracking)
2. Prometheus alert rules (high cost, token anomalies)
3. Documentation updates

**Sub-Tasks**:

- [ ] 3.1: Create Grafana dashboard for token metrics (1.5h)
- [ ] 3.2: Add Prometheus alert rules (1h)
- [ ] 3.3: Update documentation (0.5h)

**Grafana Queries**:

```promql
# Token usage per agent (last 1h)
rate(llm_tokens_total[1h]) by (agent, type)

# Cost per agent (last 24h)
increase(llm_cost_usd_total[24h]) by (agent)

# Average latency per agent
rate(llm_latency_seconds_sum[5m]) / rate(llm_latency_seconds_count[5m])
```

---

### Phase 4: Testing & Deployment (3 hours)

**Deliverables**:

1. Integration tests (config validation, token tracking)
2. Migration script (backup old configs)
3. Deployment to production droplet

**Sub-Tasks**:

- [ ] 4.1: Write integration tests (1.5h)
- [ ] 4.2: Create migration script (0.5h)
- [ ] 4.3: Deploy to droplet + validation (1h)

**Tests**:

```python
# test_config_refactoring.py
def test_yaml_loader():
    """Test YAML config loads and validates"""
    loader = ConfigLoader("config/agents/models.yaml")
    assert "orchestrator" in loader.get_all_agents()

def test_hot_reload():
    """Test config hot-reload works"""
    loader = ConfigLoader()
    original_model = loader.get_agent_config("orchestrator").model
    # Change YAML file
    loader.reload()
    new_model = loader.get_agent_config("orchestrator").model
    assert original_model != new_model

def test_token_tracking():
    """Test token metrics recorded"""
    from shared.lib.token_tracker import token_tracker
    token_tracker.track("test", 100, 50, 0.001, 0.5)
    summary = token_tracker.get_summary()
    assert "test" in summary
    assert summary["test"]["total_tokens"] == 150
```

---

## Migration Strategy

### Backward Compatibility

During migration, support both old and new configs:

```python
# shared/lib/langchain_gradient.py (TRANSITION)
try:
    # Try new YAML-based config
    config_loader = get_config_loader()
    USE_YAML_CONFIG = True
except FileNotFoundError:
    # Fallback to hardcoded config
    USE_YAML_CONFIG = False
    logger.warning("YAML config not found, using hardcoded values")

def get_llm(agent_name: str, **kwargs):
    if USE_YAML_CONFIG:
        return _get_llm_from_yaml(agent_name, **kwargs)
    else:
        return _get_llm_legacy(agent_name, **kwargs)
```

### Rollback Plan

1. **If YAML config fails**: Container falls back to hardcoded Python config
2. **If token tracking breaks**: Disable via `ENABLE_TOKEN_TRACKING=false` env var
3. **If Prometheus metrics fail**: Token tracking continues, metrics export skipped

---

## Success Metrics

| Metric                   | Baseline            | Target              | Validation                 |
| ------------------------ | ------------------- | ------------------- | -------------------------- |
| Model change time        | 30 min (rebuild)    | 30 sec (restart)    | Measure end-to-end         |
| Config drift incidents   | 2-3/week            | 0                   | Monitor for 2 weeks        |
| Token visibility latency | 5+ min (LangSmith)  | <1 sec (real-time)  | Test `/metrics/tokens`     |
| Cost attribution         | Manual              | Automatic per-agent | Verify Prometheus counters |
| A/B test complexity      | High (code changes) | Low (YAML edit)     | Compare workflows          |

---

## Documentation Updates

1. **README.md**: Add "Model Configuration" section
2. **DEPLOYMENT_GUIDE.md**: Hot-reload procedure
3. **OBSERVABILITY_GUIDE.md**: Token tracking, Grafana dashboards
4. **copilot-instructions.md**: Update LLM architecture section

---

## Linear Tracking

**Parent Issue**: DEV-XXX - LLM Configuration Refactoring & Token Metrics  
**Sub-Issues**:

- DEV-XXX+1: Phase 1 - Configuration Refactoring (5 tasks)
- DEV-XXX+2: Phase 2 - Token Tracking Integration (4 tasks)
- DEV-XXX+3: Phase 3 - Observability & Dashboards (3 tasks)
- DEV-XXX+4: Phase 4 - Testing & Deployment (3 tasks)

---

## Next Steps

1. ✅ Create Linear parent issue + sub-issues
2. ✅ Start Phase 1.1: Create YAML schema
3. Run validation after each sub-task
4. Deploy to droplet after Phase 4
5. Monitor metrics for 1 week
6. Iterate based on real-world usage

---

**Last Updated**: November 24, 2025  
**Document Owner**: Orchestrator Agent  
**Status**: Ready for Implementation

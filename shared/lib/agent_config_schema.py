"""
Agent Configuration Schema - Pydantic Models for YAML Validation

Enforces:
- Required fields (model, temperature, max_tokens)
- Valid ranges (temperature 0-1, max_tokens >= 256 for Gradient)
- Cost tracking metadata
- Environment override support
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class AgentConfig(BaseModel):
    """Configuration for a single agent's LLM instance."""

    model: str = Field(
        ...,
        description="LLM model name (e.g., 'llama3.3-70b-instruct', 'codellama-13b')",
    )
    provider: Literal["gradient", "claude", "mistral", "openai"] = Field(
        default="gradient", description="LLM provider to use"
    )
    temperature: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 = deterministic, 1.0 = creative)",
    )
    max_tokens: int = Field(
        ..., gt=0, description="Maximum tokens to generate per response"
    )
    cost_per_1m_tokens: float = Field(
        ..., ge=0.0, description="Cost per 1M tokens (for budget tracking)"
    )
    context_window: int = Field(
        ..., gt=0, description="Model context window size in tokens"
    )
    use_case: str = Field(
        ...,
        description="Primary use case for this agent (complex_reasoning, code_generation, etc.)",
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorization and filtering"
    )
    langsmith_project: str = Field(
        ...,
        description="LangSmith project name for tracing (format: agents-{agent_name})",
    )

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens_for_gradient(cls, v: int, info) -> int:
        """Gradient AI requires max_tokens >= 256."""
        provider = info.data.get("provider", "gradient")
        if provider == "gradient" and v < 256:
            raise ValueError(
                f"Gradient AI requires max_tokens >= 256, got {v}. "
                "See: https://docs.digitalocean.com/products/gen-ai-platform/reference/supported-models/"
            )
        return v

    @field_validator("langsmith_project")
    @classmethod
    def validate_langsmith_project_format(cls, v: str) -> str:
        """Ensure LangSmith project follows agents-{name} convention."""
        if not v.startswith("agents-"):
            raise ValueError(f"LangSmith project must start with 'agents-', got: {v}")
        return v


class EnvironmentOverrides(BaseModel):
    """Environment-specific configuration overrides (production, development, staging)."""

    # Agent-specific overrides (partial configs)
    orchestrator: Optional[Dict[str, str | int | float]] = Field(
        default=None, description="Override orchestrator config in this environment"
    )
    feature_dev: Optional[Dict[str, str | int | float]] = Field(
        default=None,
        description="Override feature-dev config in this environment",
        alias="feature-dev",
    )
    code_review: Optional[Dict[str, str | int | float]] = Field(
        default=None,
        description="Override code-review config in this environment",
        alias="code-review",
    )
    infrastructure: Optional[Dict[str, str | int | float]] = Field(
        default=None, description="Override infrastructure config in this environment"
    )
    cicd: Optional[Dict[str, str | int | float]] = Field(
        default=None, description="Override cicd config in this environment"
    )
    documentation: Optional[Dict[str, str | int | float]] = Field(
        default=None, description="Override documentation config in this environment"
    )


class ModelsConfig(BaseModel):
    """Root configuration schema for models.yaml."""

    version: str = Field(..., description="Config schema version (semantic versioning)")
    provider: Literal["gradient", "claude", "mistral", "openai"] = Field(
        default="gradient", description="Default LLM provider for all agents"
    )
    agents: Dict[str, AgentConfig] = Field(
        ..., description="Agent configurations keyed by agent name"
    )
    environments: Optional[Dict[str, EnvironmentOverrides]] = Field(
        default=None,
        description="Environment-specific overrides (production, development, staging)",
    )

    @field_validator("agents")
    @classmethod
    def validate_required_agents(
        cls, v: Dict[str, AgentConfig]
    ) -> Dict[str, AgentConfig]:
        """Ensure all 6 core agents are defined."""
        required_agents = {
            "orchestrator",
            "feature-dev",
            "code-review",
            "infrastructure",
            "cicd",
            "documentation",
        }
        missing = required_agents - set(v.keys())
        if missing:
            raise ValueError(
                f"Missing required agent configurations: {missing}. "
                f"All 6 agents must be defined: {required_agents}"
            )
        return v

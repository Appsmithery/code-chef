"""
Agent Configuration Schema - Pydantic Models for YAML Validation

Enforces:
- Required fields (model, temperature, max_tokens)
- Valid ranges (temperature 0-1, max_tokens >= 256 for Gradient)
- Cost tracking metadata
- Environment override support
- Error recovery configuration validation
"""

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Error Recovery Configuration Schemas
# =============================================================================


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for error recovery."""

    enabled: bool = Field(
        default=True, description="Whether circuit breaker is enabled for this agent"
    )
    use_defaults: bool = Field(
        default=True, description="Use defaults from config/error-handling.yaml"
    )
    failure_threshold: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of failures before circuit opens (1-20)",
    )
    recovery_timeout_seconds: Optional[int] = Field(
        default=None,
        ge=10,
        le=600,
        description="Seconds before attempting recovery (10-600)",
    )


class CategoryOverrideConfig(BaseModel):
    """Category-specific error recovery overrides."""

    max_tier: Optional[Literal["TIER_0", "TIER_1", "TIER_2", "TIER_3", "TIER_4"]] = (
        Field(default=None, description="Maximum recovery tier for this category")
    )
    max_retries: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Maximum retry attempts for this category (0-10)",
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=600,
        description="Timeout in seconds for this category (1-600)",
    )
    fail_fast: Optional[bool] = Field(
        default=None, description="Escalate immediately on non-retriable errors"
    )


class ErrorRecoveryConfig(BaseModel):
    """Error recovery configuration for agents and workflows.

    Integrated with ErrorRecoveryEngine for tiered recovery behavior.
    Can be specified in:
    - Agent tools.yaml (per-agent config)
    - Workflow templates (per-workflow config)
    - config/error-handling.yaml (global overrides)
    """

    enabled: bool = Field(default=True, description="Whether error recovery is enabled")
    max_tier: Literal["TIER_0", "TIER_1", "TIER_2", "TIER_3", "TIER_4"] = Field(
        default="TIER_2",
        description="Maximum recovery tier (TIER_0=instant, TIER_1=auto, TIER_2=RAG, TIER_3=agent, TIER_4=HITL)",
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts (0-10)"
    )
    fail_fast: bool = Field(
        default=False, description="Escalate immediately on non-retriable errors"
    )
    category_overrides: Optional[Dict[str, CategoryOverrideConfig]] = Field(
        default=None,
        description="Category-specific recovery overrides (llm, mcp, network, docker, auth, database)",
    )
    circuit_breaker: Optional[CircuitBreakerConfig] = Field(
        default=None, description="Circuit breaker configuration"
    )

    @field_validator("max_tier")
    @classmethod
    def validate_tier_format(cls, v: str) -> str:
        """Ensure tier follows TIER_N format."""
        valid_tiers = {"TIER_0", "TIER_1", "TIER_2", "TIER_3", "TIER_4"}
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier '{v}'. Must be one of: {valid_tiers}")
        return v

    @field_validator("category_overrides")
    @classmethod
    def validate_categories(
        cls, v: Optional[Dict[str, CategoryOverrideConfig]]
    ) -> Optional[Dict[str, CategoryOverrideConfig]]:
        """Validate category names are recognized."""
        if v is None:
            return v
        valid_categories = {
            "llm",
            "mcp",
            "network",
            "docker",
            "auth",
            "database",
            "dependency",
        }
        for category in v.keys():
            if category not in valid_categories:
                # Warn but don't fail for extensibility
                import logging

                logging.getLogger(__name__).warning(
                    f"Unrecognized error category '{category}'. "
                    f"Standard categories: {valid_categories}"
                )
        return v


class FallbackModelConfig(BaseModel):
    """LLM fallback model configuration."""

    model: str = Field(
        ...,
        description="Model name (e.g., 'llama3.3-70b-instruct', 'anthropic/claude-3-5-sonnet')",
    )
    provider: Literal["openai", "claude", "mistral", "openrouter"] = Field(
        default="openrouter", description="Model provider"
    )
    timeout_seconds: int = Field(
        default=60, ge=10, le=300, description="Timeout for this fallback model"
    )


class AgentErrorRecoveryOverride(BaseModel):
    """Per-agent error recovery configuration in models.yaml."""

    max_tier: Literal["TIER_0", "TIER_1", "TIER_2", "TIER_3", "TIER_4"] = Field(
        default="TIER_2", description="Maximum recovery tier for this agent"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )
    fail_fast: bool = Field(
        default=False, description="Escalate immediately on non-retriable errors"
    )
    fallback_chain: Optional[List[FallbackModelConfig]] = Field(
        default=None, description="Ordered list of fallback models for LLM errors"
    )


class ErrorRecoveryModelsConfig(BaseModel):
    """Error recovery configuration in models.yaml."""

    enabled: bool = Field(
        default=True, description="Whether error recovery is enabled globally"
    )
    config_path: str = Field(
        default="config/error-handling.yaml",
        description="Path to main error handling configuration",
    )
    defaults: Optional[ErrorRecoveryConfig] = Field(
        default=None, description="Default error recovery settings for all agents"
    )
    agent_overrides: Optional[Dict[str, AgentErrorRecoveryOverride]] = Field(
        default=None, description="Per-agent error recovery overrides"
    )


# =============================================================================
# Agent Configuration Schemas
# =============================================================================


class AgentConfig(BaseModel):
    """Configuration for a single agent's LLM instance."""

    model: str = Field(
        ...,
        description="LLM model name (e.g., 'llama3.3-70b-instruct', 'anthropic/claude-3-5-sonnet')",
    )
    provider: Literal["claude", "mistral", "openai", "openrouter"] = Field(
        default="openrouter", description="LLM provider to use"
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
        description="LangSmith project name for tracing (format: code-chef-{agent_name})",
    )

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens_for_gradient(cls, v: int, info) -> int:
        """OpenRouter and other providers have flexible max_tokens requirements."""
        # No minimum validation needed for OpenRouter
        if v < 1:
            raise ValueError(f"max_tokens must be at least 1, got {v}")
        return v

    @field_validator("langsmith_project")
    @classmethod
    def validate_langsmith_project_format(cls, v: str) -> str:
        """Ensure LangSmith project follows code-chef-{name} convention."""
        if not v.startswith("code-chef-"):
            raise ValueError(
                f"LangSmith project must start with 'code-chef-', got: {v}"
            )
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
    provider: Literal["claude", "mistral", "openai", "openrouter"] = Field(
        default="openrouter", description="Default LLM provider for all agents"
    )
    agents: Dict[str, AgentConfig] = Field(
        ..., description="Agent configurations keyed by agent name"
    )
    environments: Optional[Dict[str, EnvironmentOverrides]] = Field(
        default=None,
        description="Environment-specific overrides (production, development, staging)",
    )
    error_recovery: Optional[ErrorRecoveryModelsConfig] = Field(
        default=None,
        description="Error recovery configuration with per-agent overrides and fallback chains",
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


# =============================================================================
# Workflow Error Handling Schemas
# =============================================================================


class WorkflowStepErrorHandling(BaseModel):
    """Error handling configuration for a workflow step."""

    step: str = Field(..., description="Step ID this error handling applies to")
    on_error: str = Field(
        ...,
        description="Step to transition to on error (e.g., 'notify_failure', 'rollback')",
    )
    max_retries: Optional[int] = Field(
        default=None, ge=0, le=10, description="Maximum retry attempts for this step"
    )
    rollback: Optional[bool] = Field(
        default=None, description="Whether to trigger rollback on failure"
    )
    recovery_tier: Optional[
        Literal["TIER_0", "TIER_1", "TIER_2", "TIER_3", "TIER_4"]
    ] = Field(default=None, description="Maximum recovery tier for this step")
    fail_fast: Optional[bool] = Field(
        default=None, description="Escalate immediately without retry"
    )
    circuit_breaker: Optional[CircuitBreakerConfig] = Field(
        default=None, description="Circuit breaker configuration for this step"
    )
    escalation_path: Optional[List[str]] = Field(
        default=None,
        description="Ordered list of agents/targets for escalation (e.g., ['supervisor', 'hitl'])",
    )


class WorkflowStepOverride(BaseModel):
    """Step-specific error recovery overrides in workflow error_recovery block."""

    max_tier: Optional[Literal["TIER_0", "TIER_1", "TIER_2", "TIER_3", "TIER_4"]] = (
        Field(default=None, description="Maximum recovery tier for this step")
    )
    max_retries: Optional[int] = Field(
        default=None, ge=0, le=10, description="Maximum retry attempts"
    )
    fail_fast: Optional[bool] = Field(
        default=None, description="Escalate immediately without retry"
    )


class WorkflowErrorRecoveryConfig(BaseModel):
    """Top-level error recovery configuration for workflow templates."""

    enabled: bool = Field(
        default=True, description="Whether error recovery is enabled for this workflow"
    )
    default_tier: Literal["TIER_0", "TIER_1", "TIER_2", "TIER_3", "TIER_4"] = Field(
        default="TIER_2", description="Default recovery tier for workflow steps"
    )
    max_workflow_retries: int = Field(
        default=2, ge=0, le=5, description="Maximum workflow-level retry attempts"
    )
    fail_fast: bool = Field(
        default=False, description="Escalate immediately on any step failure"
    )
    step_overrides: Optional[Dict[str, WorkflowStepOverride]] = Field(
        default=None, description="Step-specific recovery overrides keyed by step ID"
    )
    llm_fallback_chain: Optional[List[FallbackModelConfig]] = Field(
        default=None,
        description="Ordered list of fallback models for LLM errors in this workflow",
    )
    escalation: Optional[Dict[str, Union[bool, str, List[str]]]] = Field(
        default=None,
        description="Escalation settings (on_any_failure, create_linear_issue, priority, notify_channels)",
    )

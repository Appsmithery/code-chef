"""Shared utilities for Dev-Tools agents."""

__all__ = [
    # Core clients
    "mcp_client",
    "gradient_client",
    "guardrail",
    "progressive_mcp_loader",
    "context7_cache",
    # Error handling
    "error_classification",
    "error_pattern_memory",
    "error_recovery_engine",
    "circuit_breaker",
    "retry_logic",
    # Qdrant
    "qdrant_client",
]

# Error classification exports
from .error_classification import (
    ErrorCategory,
    ErrorSeverity,
    RecoveryTier,
    ErrorClassification,
    ErrorSignature,
    classify_error,
    get_error_signature,
    is_retriable,
    needs_human_intervention,
)

# Error pattern memory exports
from .error_pattern_memory import (
    ErrorPattern,
    PatternMatch,
    ResolutionStep,
    ErrorPatternMemory,
    get_error_pattern_memory,
    store_error_pattern,
    find_similar_error_patterns,
)

# Error recovery engine exports
from .error_recovery_engine import (
    RecoveryResult,
    RecoveryAttempt,
    RecoveryContext,
    RecoveryOutcome,
    ErrorRecoveryEngine,
    get_error_recovery_engine,
    with_recovery,
)

# Circuit breaker exports
from .circuit_breaker import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)

# Qdrant client exports
from .qdrant_client import (
    QdrantCloudClient,
    get_qdrant_client,
)

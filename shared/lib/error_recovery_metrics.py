"""
Prometheus Metrics for Error Recovery System.

Provides observability for the self-healing architecture with metrics for:
- Recovery success rate by tier
- Time-to-recovery by error category
- Circuit breaker state changes
- Error pattern cache hit rate

Exports:
    - error_recovery_metrics: Module with all metric definitions
    - record_recovery_attempt: Function to record a recovery attempt
    - record_circuit_breaker_change: Function to record state changes
    - record_pattern_cache_hit: Function to record pattern cache hits/misses

Configuration: config/error-handling.yaml -> metrics section
"""

import logging
from typing import Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Stub classes for when prometheus_client is not installed
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def inc(self, *args, **kwargs): pass
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def observe(self, *args, **kwargs): pass
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
    class Info:
        def __init__(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass

logger = logging.getLogger(__name__)

# Namespace and subsystem from config
NAMESPACE = "codechef"
SUBSYSTEM = "error_recovery"

# ============================================================================
# Counter Metrics
# ============================================================================

# Recovery attempts by tier, category, and result
recovery_attempts_total = Counter(
    f"{NAMESPACE}_{SUBSYSTEM}_recovery_attempts_total",
    "Total number of error recovery attempts",
    ["tier", "category", "result"]
)

# Errors classified by category and severity
errors_classified_total = Counter(
    f"{NAMESPACE}_{SUBSYSTEM}_errors_classified_total",
    "Total number of errors classified",
    ["category", "severity"]
)

# Circuit breaker state changes
circuit_breaker_state_changes_total = Counter(
    f"{NAMESPACE}_{SUBSYSTEM}_circuit_breaker_state_changes_total",
    "Total number of circuit breaker state changes",
    ["circuit_name", "from_state", "to_state"]
)

# Pattern cache hits and misses
pattern_cache_operations_total = Counter(
    f"{NAMESPACE}_{SUBSYSTEM}_pattern_cache_operations_total",
    "Total pattern cache operations",
    ["operation"]  # hit, miss, store
)

# Tier escalations
tier_escalations_total = Counter(
    f"{NAMESPACE}_{SUBSYSTEM}_tier_escalations_total",
    "Total tier escalations during recovery",
    ["from_tier", "to_tier", "category"]
)

# HITL escalations (Tier 4)
hitl_escalations_total = Counter(
    f"{NAMESPACE}_{SUBSYSTEM}_hitl_escalations_total",
    "Total escalations to human-in-the-loop",
    ["category", "severity"]
)

# Loop detections
loop_detections_total = Counter(
    f"{NAMESPACE}_{SUBSYSTEM}_loop_detections_total",
    "Total recovery loop detections",
    ["category"]
)

# ============================================================================
# Histogram Metrics
# ============================================================================

# Recovery duration by tier and category
recovery_duration_seconds = Histogram(
    f"{NAMESPACE}_{SUBSYSTEM}_recovery_duration_seconds",
    "Time spent in recovery by tier and category",
    ["tier", "category"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 30.0, 120.0]
)

# Time to recovery (total time from error to resolution)
time_to_recovery_seconds = Histogram(
    f"{NAMESPACE}_{SUBSYSTEM}_time_to_recovery_seconds",
    "Total time from error occurrence to successful recovery",
    ["category"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# Pattern similarity scores
pattern_similarity_scores = Histogram(
    f"{NAMESPACE}_{SUBSYSTEM}_pattern_similarity_scores",
    "Distribution of pattern similarity scores",
    ["category"],
    buckets=[0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
)

# ============================================================================
# Gauge Metrics
# ============================================================================

# Current circuit breaker states (0=closed, 1=half-open, 2=open)
circuit_breaker_state = Gauge(
    f"{NAMESPACE}_{SUBSYSTEM}_circuit_breaker_state",
    "Current state of circuit breakers (0=closed, 1=half-open, 2=open)",
    ["circuit_name"]
)

# Pattern cache size
pattern_cache_size = Gauge(
    f"{NAMESPACE}_{SUBSYSTEM}_pattern_cache_size",
    "Number of patterns in local cache",
    []
)

# Recovery success rate by tier (calculated gauge)
recovery_success_rate = Gauge(
    f"{NAMESPACE}_{SUBSYSTEM}_recovery_success_rate",
    "Success rate of recovery by tier (0.0 to 1.0)",
    ["tier"]
)

# Active recovery operations
active_recoveries = Gauge(
    f"{NAMESPACE}_{SUBSYSTEM}_active_recoveries",
    "Number of currently active recovery operations",
    ["tier"]
)

# ============================================================================
# Info Metrics
# ============================================================================

# Error recovery system info
error_recovery_info = Info(
    f"{NAMESPACE}_{SUBSYSTEM}_info",
    "Information about error recovery system configuration"
)

# ============================================================================
# Helper Functions
# ============================================================================

def record_recovery_attempt(
    tier: int,
    category: str,
    result: str,
    duration_seconds: float,
):
    """Record a recovery attempt with all relevant metrics.
    
    Args:
        tier: Recovery tier (0-4)
        category: Error category (network, auth, llm, etc.)
        result: Result of attempt (success, failure, escalated, circuit_open)
        duration_seconds: Time spent in this attempt
    """
    tier_str = f"tier_{tier}"
    
    # Increment counter
    recovery_attempts_total.labels(
        tier=tier_str,
        category=category,
        result=result,
    ).inc()
    
    # Record duration
    recovery_duration_seconds.labels(
        tier=tier_str,
        category=category,
    ).observe(duration_seconds)
    
    logger.debug(
        f"[Metrics] Recovery attempt: tier={tier}, category={category}, "
        f"result={result}, duration={duration_seconds:.3f}s"
    )


def record_error_classified(category: str, severity: str):
    """Record an error classification.
    
    Args:
        category: Error category
        severity: Error severity (low, medium, high, critical)
    """
    errors_classified_total.labels(
        category=category,
        severity=severity,
    ).inc()


def record_circuit_breaker_change(
    circuit_name: str,
    from_state: str,
    to_state: str,
):
    """Record a circuit breaker state change.
    
    Args:
        circuit_name: Name of the circuit breaker
        from_state: Previous state (closed, half_open, open)
        to_state: New state
    """
    circuit_breaker_state_changes_total.labels(
        circuit_name=circuit_name,
        from_state=from_state,
        to_state=to_state,
    ).inc()
    
    # Update gauge
    state_values = {"closed": 0, "half_open": 1, "open": 2}
    circuit_breaker_state.labels(circuit_name=circuit_name).set(
        state_values.get(to_state, 0)
    )
    
    logger.info(
        f"[Metrics] Circuit breaker '{circuit_name}': {from_state} -> {to_state}"
    )


def record_pattern_cache_hit(hit: bool):
    """Record a pattern cache hit or miss.
    
    Args:
        hit: True if pattern was found in cache, False otherwise
    """
    pattern_cache_operations_total.labels(
        operation="hit" if hit else "miss"
    ).inc()


def record_pattern_stored():
    """Record a new pattern being stored."""
    pattern_cache_operations_total.labels(operation="store").inc()


def record_tier_escalation(
    from_tier: int,
    to_tier: int,
    category: str,
):
    """Record a tier escalation.
    
    Args:
        from_tier: Previous tier
        to_tier: New tier
        category: Error category
    """
    tier_escalations_total.labels(
        from_tier=f"tier_{from_tier}",
        to_tier=f"tier_{to_tier}",
        category=category,
    ).inc()


def record_hitl_escalation(category: str, severity: str):
    """Record an escalation to human-in-the-loop.
    
    Args:
        category: Error category
        severity: Error severity
    """
    hitl_escalations_total.labels(
        category=category,
        severity=severity,
    ).inc()


def record_loop_detection(category: str):
    """Record a recovery loop detection.
    
    Args:
        category: Error category that triggered loop detection
    """
    loop_detections_total.labels(category=category).inc()


def record_time_to_recovery(category: str, total_seconds: float):
    """Record total time to recovery.
    
    Args:
        category: Error category
        total_seconds: Total time from error to successful recovery
    """
    time_to_recovery_seconds.labels(category=category).observe(total_seconds)


def record_pattern_similarity(category: str, score: float):
    """Record a pattern similarity score.
    
    Args:
        category: Error category
        score: Similarity score (0.0 to 1.0)
    """
    pattern_similarity_scores.labels(category=category).observe(score)


def update_cache_size(size: int):
    """Update the pattern cache size gauge.
    
    Args:
        size: Current number of patterns in cache
    """
    pattern_cache_size.set(size)


def update_success_rate(tier: int, rate: float):
    """Update the success rate gauge for a tier.
    
    Args:
        tier: Recovery tier (0-4)
        rate: Success rate (0.0 to 1.0)
    """
    recovery_success_rate.labels(tier=f"tier_{tier}").set(rate)


def start_recovery(tier: int):
    """Mark a recovery as started (increment active count).
    
    Args:
        tier: Recovery tier
    """
    active_recoveries.labels(tier=f"tier_{tier}").inc()


def end_recovery(tier: int):
    """Mark a recovery as ended (decrement active count).
    
    Args:
        tier: Recovery tier
    """
    active_recoveries.labels(tier=f"tier_{tier}").dec()


def set_system_info(version: str, config_version: str):
    """Set error recovery system info.
    
    Args:
        version: System version
        config_version: Configuration version
    """
    if PROMETHEUS_AVAILABLE:
        error_recovery_info.info({
            "version": version,
            "config_version": config_version,
            "prometheus_enabled": "true",
        })


# Initialize info on module load
if PROMETHEUS_AVAILABLE:
    try:
        set_system_info("1.0.0", "1.0")
    except Exception:
        pass  # Ignore initialization errors

"""
Error Recovery Engine for Code-Chef Self-Healing Architecture.

Orchestrates tiered error recovery across 5 tiers:
    - Tier 0: Instant heuristic triage (<10ms, 0 tokens)
    - Tier 1: Automatic remediation (<5s, 0 tokens)
    - Tier 2: RAG-assisted recovery (<30s, ~50 tokens)
    - Tier 3: Agent-assisted diagnosis (<2min, ~500 tokens)
    - Tier 4: Human-in-the-loop escalation (async)

Integrates:
    - Error classification for routing decisions
    - Circuit breakers for failure isolation
    - Error pattern memory for RAG recovery
    - Loop protection to prevent infinite recovery cycles
    - Prometheus metrics for observability

Configuration: config/error-handling.yaml
"""

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union
import yaml

from .error_classification import (
    ErrorCategory,
    ErrorClassification,
    ErrorSeverity,
    ErrorSignature,
    RecoveryTier,
    classify_error,
    get_error_signature,
)
from .error_pattern_memory import (
    ErrorPatternMemory,
    PatternMatch,
    ResolutionStep,
    get_error_pattern_memory,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _load_config() -> Dict[str, Any]:
    """Load error handling configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "config", "error-handling.yaml"
    )
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load error-handling.yaml: {e}")
        return {}


class RecoveryResult(str, Enum):
    """Result of a recovery attempt."""
    
    SUCCESS = "success"           # Error was recovered
    FAILURE = "failure"           # Recovery failed, may escalate
    ESCALATED = "escalated"       # Escalated to higher tier
    CIRCUIT_OPEN = "circuit_open" # Circuit breaker blocked attempt
    LOOP_DETECTED = "loop_detected" # Recovery loop detected
    SKIPPED = "skipped"           # Recovery not applicable


@dataclass
class RecoveryAttempt:
    """Record of a single recovery attempt."""
    
    tier: RecoveryTier
    action: str
    result: RecoveryResult
    duration_seconds: float
    error_message: Optional[str] = None
    tokens_used: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RecoveryContext:
    """Context for error recovery."""
    
    exception: Exception
    classification: ErrorClassification
    signature: ErrorSignature
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    agent_name: Optional[str] = None
    attempt_count: int = 0
    tier_escalations: int = 0
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    pattern_matches: List[PatternMatch] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_duration_seconds(self) -> float:
        """Total time spent in recovery."""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    @property
    def total_tokens_used(self) -> int:
        """Total tokens used across all attempts."""
        return sum(a.tokens_used for a in self.attempts)


@dataclass
class RecoveryOutcome:
    """Final outcome of error recovery."""
    
    success: bool
    final_tier: RecoveryTier
    result: RecoveryResult
    context: RecoveryContext
    recovery_value: Any = None  # Value returned from successful recovery
    error: Optional[Exception] = None  # Error if recovery failed
    linear_issue_id: Optional[str] = None  # For Tier 4 escalations
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Metrics for this recovery."""
        return {
            "success": self.success,
            "final_tier": self.final_tier.value,
            "result": self.result.value,
            "total_attempts": len(self.context.attempts),
            "tier_escalations": self.context.tier_escalations,
            "total_duration_seconds": self.context.total_duration_seconds,
            "total_tokens_used": self.context.total_tokens_used,
            "category": self.context.classification.category.value,
            "severity": self.context.classification.severity.value,
        }


class LoopProtection:
    """Protects against infinite recovery loops."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or _load_config().get("loop_protection", {})
        self._error_counts: Dict[str, List[datetime]] = {}  # signature -> timestamps
        self._workflow_escalations: Dict[str, int] = {}  # workflow_id -> count
        self._lock = asyncio.Lock()
    
    async def check_loop(
        self,
        signature: ErrorSignature,
        workflow_id: Optional[str] = None,
    ) -> bool:
        """Check if we're in a recovery loop.
        
        Returns:
            True if loop detected (should stop recovery)
        """
        async with self._lock:
            signature_key = signature.to_key()
            now = datetime.utcnow()
            
            # Check per-error loop
            window_seconds = self._config.get("loop_detection", {}).get("window_seconds", 60)
            max_identical = self._config.get("loop_detection", {}).get("max_identical_errors", 3)
            
            cutoff = now - timedelta(seconds=window_seconds)
            
            if signature_key in self._error_counts:
                # Remove old timestamps
                self._error_counts[signature_key] = [
                    ts for ts in self._error_counts[signature_key] if ts > cutoff
                ]
                
                if len(self._error_counts[signature_key]) >= max_identical:
                    logger.warning(f"Loop detected for error {signature_key}: {len(self._error_counts[signature_key])} occurrences in {window_seconds}s")
                    return True
            
            # Check workflow escalation limit
            if workflow_id:
                max_escalations = self._config.get("max_tier_escalations_per_workflow", 10)
                current = self._workflow_escalations.get(workflow_id, 0)
                if current >= max_escalations:
                    logger.warning(f"Workflow {workflow_id} exceeded max tier escalations: {current}")
                    return True
            
            return False
    
    async def record_error(
        self,
        signature: ErrorSignature,
        workflow_id: Optional[str] = None,
    ):
        """Record an error occurrence."""
        async with self._lock:
            signature_key = signature.to_key()
            now = datetime.utcnow()
            
            if signature_key not in self._error_counts:
                self._error_counts[signature_key] = []
            self._error_counts[signature_key].append(now)
    
    async def record_escalation(self, workflow_id: str):
        """Record a tier escalation for a workflow."""
        async with self._lock:
            self._workflow_escalations[workflow_id] = (
                self._workflow_escalations.get(workflow_id, 0) + 1
            )
    
    async def reset_workflow(self, workflow_id: str):
        """Reset counters for a workflow (on success or new run)."""
        async with self._lock:
            if workflow_id in self._workflow_escalations:
                del self._workflow_escalations[workflow_id]


class ErrorRecoveryEngine:
    """
    Orchestrates tiered error recovery across all tiers.
    
    Usage:
        engine = ErrorRecoveryEngine()
        
        try:
            result = await some_operation()
        except Exception as e:
            outcome = await engine.recover(
                exception=e,
                workflow_id="wf-123",
                step_id="step-1",
                operation=some_operation,  # For automatic retry
            )
            
            if outcome.success:
                result = outcome.recovery_value
            else:
                # Handle unrecoverable error
                raise outcome.error
    """
    
    def __init__(
        self,
        pattern_memory: Optional[ErrorPatternMemory] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the error recovery engine.
        
        Args:
            pattern_memory: Error pattern memory for Tier 2 recovery
            config: Configuration override (defaults to error-handling.yaml)
        """
        self._config = config or _load_config()
        self._pattern_memory = pattern_memory or get_error_pattern_memory()
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._loop_protection = LoopProtection(self._config.get("loop_protection"))
        self._lock = asyncio.Lock()
        
        # Event callbacks
        self._on_recovery_start: Optional[Callable] = None
        self._on_recovery_complete: Optional[Callable] = None
        self._on_tier_escalation: Optional[Callable] = None
        
        logger.info("Error recovery engine initialized")
    
    def set_callbacks(
        self,
        on_recovery_start: Optional[Callable] = None,
        on_recovery_complete: Optional[Callable] = None,
        on_tier_escalation: Optional[Callable] = None,
    ):
        """Set event callbacks for observability."""
        self._on_recovery_start = on_recovery_start
        self._on_recovery_complete = on_recovery_complete
        self._on_tier_escalation = on_tier_escalation
    
    def _get_circuit_breaker(self, key: str, category: ErrorCategory) -> CircuitBreaker:
        """Get or create circuit breaker for a key."""
        if key not in self._circuit_breakers:
            # Load config for this category
            cb_config = self._config.get("circuit_breaker", {})
            category_config = cb_config.get("per_category", {}).get(
                category.value, cb_config.get("default", {})
            )
            
            config = CircuitBreakerConfig.from_dict(category_config)
            self._circuit_breakers[key] = CircuitBreaker(
                name=key,
                config=config,
                on_state_change=self._on_circuit_state_change,
            )
        
        return self._circuit_breakers[key]
    
    def _on_circuit_state_change(
        self,
        name: str,
        old_state: CircuitState,
        new_state: CircuitState,
    ):
        """Handle circuit breaker state changes."""
        logger.info(f"Circuit breaker '{name}': {old_state.value} -> {new_state.value}")
        # TODO: Emit Prometheus metric
    
    def _get_retry_config(self, category: ErrorCategory) -> Dict[str, Any]:
        """Get retry configuration for a category."""
        retry_config = self._config.get("retry", {})
        return retry_config.get("per_category", {}).get(
            category.value, retry_config.get("default", {})
        )
    
    def _calculate_backoff(
        self,
        attempt: int,
        config: Dict[str, Any],
    ) -> float:
        """Calculate backoff delay with jitter."""
        initial = config.get("initial_delay_seconds", 1.0)
        max_delay = config.get("max_delay_seconds", 60.0)
        base = config.get("exponential_base", 2.0)
        jitter_enabled = config.get("jitter", True)
        jitter_percent = config.get("jitter_percent", 0.25)
        
        delay = min(initial * (base ** attempt), max_delay)
        
        if jitter_enabled:
            jitter = delay * jitter_percent
            delay = delay + random.uniform(-jitter, jitter)
        
        return max(0, delay)
    
    async def recover(
        self,
        exception: Exception,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        operation: Optional[Callable[[], Awaitable[T]]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_tier: RecoveryTier = RecoveryTier.TIER_4,
    ) -> RecoveryOutcome:
        """
        Attempt to recover from an error using tiered recovery.
        
        Args:
            exception: The exception to recover from
            workflow_id: Optional workflow ID for tracking
            step_id: Optional step ID for circuit breaker keys
            agent_name: Optional agent name for routing
            operation: Optional async callable to retry on success
            context: Additional context for pattern matching
            max_tier: Maximum tier to escalate to (default: TIER_4)
        
        Returns:
            RecoveryOutcome with success status and recovery value or error
        """
        # Classify the error
        classification = classify_error(exception, context)
        signature = get_error_signature(exception, classification)
        
        # Create recovery context
        recovery_ctx = RecoveryContext(
            exception=exception,
            classification=classification,
            signature=signature,
            workflow_id=workflow_id,
            step_id=step_id,
            agent_name=agent_name,
        )
        
        # Check for recovery loops
        if await self._loop_protection.check_loop(signature, workflow_id):
            logger.error(f"Recovery loop detected for {signature.to_key()}, escalating to HITL")
            return RecoveryOutcome(
                success=False,
                final_tier=RecoveryTier.TIER_4,
                result=RecoveryResult.LOOP_DETECTED,
                context=recovery_ctx,
                error=exception,
            )
        
        # Record error occurrence
        await self._loop_protection.record_error(signature, workflow_id)
        
        # Emit start event
        if self._on_recovery_start:
            await self._safe_callback(self._on_recovery_start, recovery_ctx)
        
        # Start tiered recovery
        current_tier = classification.suggested_tier
        
        while current_tier.value <= max_tier.value:
            logger.info(
                f"Attempting Tier {current_tier.value} recovery for {classification.category.value} error"
            )
            
            try:
                outcome = await self._execute_tier(
                    tier=current_tier,
                    context=recovery_ctx,
                    operation=operation,
                )
                
                if outcome.success:
                    # Store successful pattern
                    if current_tier.value >= RecoveryTier.TIER_1.value:
                        await self._store_successful_pattern(recovery_ctx, outcome)
                    
                    # Reset workflow counters on success
                    if workflow_id:
                        await self._loop_protection.reset_workflow(workflow_id)
                    
                    # Emit completion event
                    if self._on_recovery_complete:
                        await self._safe_callback(self._on_recovery_complete, outcome)
                    
                    return outcome
                
                # Check if we should escalate
                if outcome.result == RecoveryResult.CIRCUIT_OPEN:
                    # Circuit is open, skip to higher tier
                    pass
                elif outcome.result == RecoveryResult.FAILURE:
                    # Recovery failed, try next tier
                    pass
                elif outcome.result == RecoveryResult.SKIPPED:
                    # This tier not applicable
                    pass
                
                # Escalate to next tier
                next_tier = RecoveryTier(current_tier.value + 1)
                if next_tier.value <= max_tier.value:
                    recovery_ctx.tier_escalations += 1
                    
                    if workflow_id:
                        await self._loop_protection.record_escalation(workflow_id)
                    
                    if self._on_tier_escalation:
                        await self._safe_callback(
                            self._on_tier_escalation, current_tier, next_tier, recovery_ctx
                        )
                    
                    current_tier = next_tier
                else:
                    # Reached max tier
                    break
                    
            except Exception as e:
                logger.error(f"Tier {current_tier.value} recovery failed with exception: {e}")
                recovery_ctx.attempts.append(RecoveryAttempt(
                    tier=current_tier,
                    action="tier_execution",
                    result=RecoveryResult.FAILURE,
                    duration_seconds=0,
                    error_message=str(e),
                ))
                
                # Try next tier
                next_tier = RecoveryTier(current_tier.value + 1)
                if next_tier.value <= max_tier.value:
                    current_tier = next_tier
                else:
                    break
        
        # All tiers exhausted
        final_outcome = RecoveryOutcome(
            success=False,
            final_tier=current_tier,
            result=RecoveryResult.FAILURE,
            context=recovery_ctx,
            error=exception,
        )
        
        if self._on_recovery_complete:
            await self._safe_callback(self._on_recovery_complete, final_outcome)
        
        return final_outcome
    
    async def _execute_tier(
        self,
        tier: RecoveryTier,
        context: RecoveryContext,
        operation: Optional[Callable[[], Awaitable[T]]] = None,
    ) -> RecoveryOutcome:
        """Execute recovery for a specific tier."""
        tier_handlers = {
            RecoveryTier.TIER_0: self._handle_tier_0,
            RecoveryTier.TIER_1: self._handle_tier_1,
            RecoveryTier.TIER_2: self._handle_tier_2,
            RecoveryTier.TIER_3: self._handle_tier_3,
            RecoveryTier.TIER_4: self._handle_tier_4,
        }
        
        handler = tier_handlers.get(tier)
        if handler is None:
            return RecoveryOutcome(
                success=False,
                final_tier=tier,
                result=RecoveryResult.SKIPPED,
                context=context,
            )
        
        return await handler(context, operation)
    
    async def _handle_tier_0(
        self,
        context: RecoveryContext,
        operation: Optional[Callable[[], Awaitable[T]]] = None,
    ) -> RecoveryOutcome:
        """
        Tier 0: Instant Heuristic Triage (<10ms, 0 tokens)
        
        Actions:
            - Error classification (already done)
            - Circuit breaker check
            - Cached resolution lookup
        """
        start_time = time.time()
        
        # Check circuit breaker
        cb_key = f"{context.step_id or 'default'}:{context.classification.category.value}"
        breaker = self._get_circuit_breaker(cb_key, context.classification.category)
        
        if breaker.state == CircuitState.OPEN:
            context.attempts.append(RecoveryAttempt(
                tier=RecoveryTier.TIER_0,
                action="circuit_breaker_check",
                result=RecoveryResult.CIRCUIT_OPEN,
                duration_seconds=time.time() - start_time,
            ))
            return RecoveryOutcome(
                success=False,
                final_tier=RecoveryTier.TIER_0,
                result=RecoveryResult.CIRCUIT_OPEN,
                context=context,
            )
        
        # Check local cache for quick resolution
        # (Tier 0 only uses local cache, not Qdrant)
        cached_pattern = self._pattern_memory._get_from_cache(context.signature.to_key())
        
        if cached_pattern and cached_pattern.is_effective:
            context.pattern_matches.append(PatternMatch(
                pattern=cached_pattern,
                similarity_score=1.0,
                is_exact_match=True,
            ))
            
            # If we have a cached pattern and operation, try immediate retry
            if operation and self._is_simple_retry(cached_pattern.resolution_steps):
                try:
                    result = await operation()
                    context.attempts.append(RecoveryAttempt(
                        tier=RecoveryTier.TIER_0,
                        action="cached_resolution_retry",
                        result=RecoveryResult.SUCCESS,
                        duration_seconds=time.time() - start_time,
                    ))
                    return RecoveryOutcome(
                        success=True,
                        final_tier=RecoveryTier.TIER_0,
                        result=RecoveryResult.SUCCESS,
                        context=context,
                        recovery_value=result,
                    )
                except Exception:
                    pass  # Fall through to next tier
        
        context.attempts.append(RecoveryAttempt(
            tier=RecoveryTier.TIER_0,
            action="heuristic_triage",
            result=RecoveryResult.ESCALATED,
            duration_seconds=time.time() - start_time,
        ))
        
        return RecoveryOutcome(
            success=False,
            final_tier=RecoveryTier.TIER_0,
            result=RecoveryResult.ESCALATED,
            context=context,
        )
    
    async def _handle_tier_1(
        self,
        context: RecoveryContext,
        operation: Optional[Callable[[], Awaitable[T]]] = None,
    ) -> RecoveryOutcome:
        """
        Tier 1: Automatic Remediation (<5s, 0 tokens)
        
        Actions:
            - Retry with exponential backoff
            - Dependency auto-install
            - Token refresh
            - Container restart
            - Context truncation
        """
        start_time = time.time()
        
        category = context.classification.category
        retry_config = self._get_retry_config(category)
        max_retries = retry_config.get("max_retries", 3)
        
        # Check if error type supports automatic retry
        if not context.classification.is_retriable:
            context.attempts.append(RecoveryAttempt(
                tier=RecoveryTier.TIER_1,
                action="retriable_check",
                result=RecoveryResult.SKIPPED,
                duration_seconds=time.time() - start_time,
            ))
            return RecoveryOutcome(
                success=False,
                final_tier=RecoveryTier.TIER_1,
                result=RecoveryResult.SKIPPED,
                context=context,
            )
        
        # Try category-specific remediation first
        remediation_result = await self._try_category_remediation(context)
        if remediation_result:
            return remediation_result
        
        # Retry with backoff if we have an operation
        if operation:
            for attempt in range(max_retries):
                delay = self._calculate_backoff(attempt, retry_config)
                
                if delay > 0:
                    await asyncio.sleep(delay)
                
                try:
                    result = await operation()
                    
                    context.attempts.append(RecoveryAttempt(
                        tier=RecoveryTier.TIER_1,
                        action=f"retry_attempt_{attempt + 1}",
                        result=RecoveryResult.SUCCESS,
                        duration_seconds=time.time() - start_time,
                    ))
                    
                    # Record success with circuit breaker
                    cb_key = f"{context.step_id or 'default'}:{category.value}"
                    breaker = self._get_circuit_breaker(cb_key, category)
                    breaker._on_success()
                    
                    return RecoveryOutcome(
                        success=True,
                        final_tier=RecoveryTier.TIER_1,
                        result=RecoveryResult.SUCCESS,
                        context=context,
                        recovery_value=result,
                    )
                    
                except Exception as e:
                    context.exception = e
                    context.attempt_count += 1
                    
                    # Record failure with circuit breaker
                    cb_key = f"{context.step_id or 'default'}:{category.value}"
                    breaker = self._get_circuit_breaker(cb_key, category)
                    breaker._on_failure(e)
        
        context.attempts.append(RecoveryAttempt(
            tier=RecoveryTier.TIER_1,
            action="retry_exhausted",
            result=RecoveryResult.FAILURE,
            duration_seconds=time.time() - start_time,
        ))
        
        return RecoveryOutcome(
            success=False,
            final_tier=RecoveryTier.TIER_1,
            result=RecoveryResult.FAILURE,
            context=context,
        )
    
    async def _try_category_remediation(
        self,
        context: RecoveryContext,
    ) -> Optional[RecoveryOutcome]:
        """Try category-specific automatic remediation."""
        category = context.classification.category
        
        if category == ErrorCategory.DEPENDENCY:
            return await self._remediate_dependency(context)
        elif category == ErrorCategory.LLM:
            return await self._remediate_llm(context)
        elif category == ErrorCategory.DOCKER:
            return await self._remediate_docker(context)
        elif category == ErrorCategory.AUTH:
            return await self._remediate_auth(context)
        
        return None
    
    async def _remediate_dependency(
        self,
        context: RecoveryContext,
    ) -> Optional[RecoveryOutcome]:
        """Auto-install missing dependency."""
        import re
        
        error_msg = str(context.exception)
        
        # Extract module name
        match = re.search(r"No module named ['\"]?([a-zA-Z0-9_-]+)", error_msg)
        if not match:
            return None
        
        module_name = match.group(1)
        
        try:
            import subprocess
            result = subprocess.run(
                ["pip", "install", module_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                logger.info(f"Auto-installed dependency: {module_name}")
                context.attempts.append(RecoveryAttempt(
                    tier=RecoveryTier.TIER_1,
                    action=f"dependency_install:{module_name}",
                    result=RecoveryResult.SUCCESS,
                    duration_seconds=0,
                ))
                # Note: Caller should retry operation after this
                return None  # Continue with retry
            
        except Exception as e:
            logger.warning(f"Failed to auto-install {module_name}: {e}")
        
        return None
    
    async def _remediate_llm(
        self,
        context: RecoveryContext,
    ) -> Optional[RecoveryOutcome]:
        """Handle LLM-specific errors (context overflow, rate limits)."""
        error_msg = str(context.exception).lower()
        
        # Check for context overflow
        if "context" in error_msg and ("overflow" in error_msg or "too long" in error_msg):
            # Flag for context truncation
            context.classification.context["needs_context_truncation"] = True
            logger.info("LLM context overflow detected, flagging for truncation")
        
        # Check for rate limit
        if "rate limit" in error_msg or "429" in error_msg:
            # Apply longer backoff (handled by retry config)
            context.classification.context["rate_limited"] = True
            logger.info("LLM rate limit detected, will apply extended backoff")
        
        return None  # Continue with standard retry
    
    async def _remediate_docker(
        self,
        context: RecoveryContext,
    ) -> Optional[RecoveryOutcome]:
        """Handle Docker-specific errors."""
        # Docker remediation would require MCP tool access
        # For now, just flag for Tier 3 agent handling
        return None
    
    async def _remediate_auth(
        self,
        context: RecoveryContext,
    ) -> Optional[RecoveryOutcome]:
        """Handle auth errors (token refresh)."""
        error_msg = str(context.exception).lower()
        
        if "token" in error_msg and ("expired" in error_msg or "invalid" in error_msg):
            # Flag for token refresh
            context.classification.context["needs_token_refresh"] = True
            logger.info("Token expiry detected, flagging for refresh")
        
        return None
    
    async def _handle_tier_2(
        self,
        context: RecoveryContext,
        operation: Optional[Callable[[], Awaitable[T]]] = None,
    ) -> RecoveryOutcome:
        """
        Tier 2: RAG-Assisted Recovery (<30s, ~50 tokens)
        
        Actions:
            - Query error pattern memory
            - Apply previous fixes
            - Store new patterns
        """
        start_time = time.time()
        
        # Search for similar patterns
        try:
            matches = await self._pattern_memory.find_similar_patterns(
                exception=context.exception,
                classification=context.classification,
                context={
                    "workflow_id": context.workflow_id,
                    "step_id": context.step_id,
                    "agent_name": context.agent_name,
                },
            )
            
            context.pattern_matches.extend(matches)
            
            if matches:
                best_match = matches[0]
                logger.info(
                    f"Found similar pattern with {best_match.confidence} confidence "
                    f"(score: {best_match.similarity_score:.2f})"
                )
                
                # Try to apply resolution steps
                if operation and best_match.pattern.resolution_steps:
                    # For now, just retry - more sophisticated step execution could be added
                    try:
                        result = await operation()
                        
                        # Record success
                        await self._pattern_memory.record_resolution_outcome(
                            pattern_id=best_match.pattern.id,
                            success=True,
                        )
                        
                        context.attempts.append(RecoveryAttempt(
                            tier=RecoveryTier.TIER_2,
                            action="pattern_resolution",
                            result=RecoveryResult.SUCCESS,
                            duration_seconds=time.time() - start_time,
                            tokens_used=50,  # Approximate for RAG lookup
                        ))
                        
                        return RecoveryOutcome(
                            success=True,
                            final_tier=RecoveryTier.TIER_2,
                            result=RecoveryResult.SUCCESS,
                            context=context,
                            recovery_value=result,
                        )
                        
                    except Exception as e:
                        # Record failure
                        await self._pattern_memory.record_resolution_outcome(
                            pattern_id=best_match.pattern.id,
                            success=False,
                        )
                        context.exception = e
            
        except Exception as e:
            logger.error(f"Pattern memory search failed: {e}")
        
        context.attempts.append(RecoveryAttempt(
            tier=RecoveryTier.TIER_2,
            action="pattern_search",
            result=RecoveryResult.ESCALATED,
            duration_seconds=time.time() - start_time,
            tokens_used=50,
        ))
        
        return RecoveryOutcome(
            success=False,
            final_tier=RecoveryTier.TIER_2,
            result=RecoveryResult.ESCALATED,
            context=context,
        )
    
    async def _handle_tier_3(
        self,
        context: RecoveryContext,
        operation: Optional[Callable[[], Awaitable[T]]] = None,
    ) -> RecoveryOutcome:
        """
        Tier 3: Agent-Assisted Diagnosis (<2min, ~500 tokens)
        
        Actions:
            - Route to infrastructure agent
            - Use MCP tools
            - Generate and execute recovery plan
        """
        start_time = time.time()
        
        # Tier 3 requires agent routing - this is a placeholder
        # In production, this would invoke the infrastructure agent
        
        tier_config = self._config.get("tiers", {}).get("tier_3", {})
        target_agent = tier_config.get("target_agent", "infrastructure")
        
        logger.info(f"Tier 3: Would route to {target_agent} agent for diagnosis")
        
        # Build diagnosis context
        diagnosis_context = {
            "error_category": context.classification.category.value,
            "error_type": context.signature.error_type,
            "error_message": str(context.exception),
            "severity": context.classification.severity.value,
            "hints": context.classification.remediation_hints,
            "workflow_id": context.workflow_id,
            "step_id": context.step_id,
            "previous_patterns": [
                {
                    "confidence": m.confidence,
                    "resolution_steps": [s.action for s in m.pattern.resolution_steps],
                }
                for m in context.pattern_matches[:3]
            ],
        }
        
        # TODO: Invoke infrastructure agent via graph
        # For now, just escalate to Tier 4
        
        context.attempts.append(RecoveryAttempt(
            tier=RecoveryTier.TIER_3,
            action="agent_diagnosis",
            result=RecoveryResult.ESCALATED,
            duration_seconds=time.time() - start_time,
            tokens_used=500,
        ))
        
        return RecoveryOutcome(
            success=False,
            final_tier=RecoveryTier.TIER_3,
            result=RecoveryResult.ESCALATED,
            context=context,
        )
    
    async def _handle_tier_4(
        self,
        context: RecoveryContext,
        operation: Optional[Callable[[], Awaitable[T]]] = None,
    ) -> RecoveryOutcome:
        """
        Tier 4: Human-in-the-Loop Escalation (async)
        
        Actions:
            - Create Linear issue
            - Pause workflow
            - Webhook notification
            - Await human decision
        """
        start_time = time.time()
        
        tier_config = self._config.get("tiers", {}).get("tier_4", {})
        linear_project = tier_config.get("linear_project", "CHEF")
        
        logger.info(f"Tier 4: Escalating to human via Linear (project: {linear_project})")
        
        # Build issue content
        issue_title = f"[Auto-Recovery] {context.classification.category.value.upper()}: {context.signature.error_type}"
        issue_body = self._build_hitl_issue_body(context)
        
        # TODO: Create Linear issue via HITLManager
        # For now, just log the escalation
        
        logger.warning(
            f"HITL Escalation Required:\n"
            f"Title: {issue_title}\n"
            f"Category: {context.classification.category.value}\n"
            f"Severity: {context.classification.severity.value}\n"
            f"Attempts: {len(context.attempts)}\n"
            f"Duration: {context.total_duration_seconds:.2f}s"
        )
        
        context.attempts.append(RecoveryAttempt(
            tier=RecoveryTier.TIER_4,
            action="hitl_escalation",
            result=RecoveryResult.ESCALATED,
            duration_seconds=time.time() - start_time,
        ))
        
        return RecoveryOutcome(
            success=False,
            final_tier=RecoveryTier.TIER_4,
            result=RecoveryResult.ESCALATED,
            context=context,
            error=context.exception,
            linear_issue_id=None,  # Would be set after issue creation
        )
    
    def _build_hitl_issue_body(self, context: RecoveryContext) -> str:
        """Build Linear issue body for HITL escalation."""
        attempts_summary = "\n".join(
            f"- Tier {a.tier.value}: {a.action} → {a.result.value} ({a.duration_seconds:.2f}s)"
            for a in context.attempts
        )
        
        hints = "\n".join(f"- {h}" for h in context.classification.remediation_hints)
        
        return f"""## Error Details

**Category:** {context.classification.category.value}
**Severity:** {context.classification.severity.value}
**Error Type:** {context.signature.error_type}

### Error Message
```
{str(context.exception)}
```

### Remediation Hints
{hints if hints else "No hints available"}

### Recovery Attempts
{attempts_summary}

### Context
- Workflow ID: {context.workflow_id or 'N/A'}
- Step ID: {context.step_id or 'N/A'}
- Agent: {context.agent_name or 'N/A'}
- Total Duration: {context.total_duration_seconds:.2f}s
- Total Tokens Used: {context.total_tokens_used}

### Pattern Matches
{self._format_pattern_matches(context.pattern_matches)}
"""
    
    def _format_pattern_matches(self, matches: List[PatternMatch]) -> str:
        """Format pattern matches for issue body."""
        if not matches:
            return "No similar patterns found"
        
        lines = []
        for m in matches[:3]:
            steps = ", ".join(s.action for s in m.pattern.resolution_steps[:3])
            lines.append(
                f"- Score: {m.similarity_score:.2f}, "
                f"Success Rate: {m.pattern.success_rate:.0%}, "
                f"Steps: {steps}"
            )
        return "\n".join(lines)
    
    async def _store_successful_pattern(
        self,
        context: RecoveryContext,
        outcome: RecoveryOutcome,
    ):
        """Store successful resolution as a pattern."""
        if not self._pattern_memory.is_enabled:
            return
        
        # Determine resolution steps from attempts
        steps = []
        for attempt in context.attempts:
            if attempt.result == RecoveryResult.SUCCESS:
                steps.append(ResolutionStep(
                    action=attempt.action,
                    tier=attempt.tier,
                    description=f"Tier {attempt.tier.value} recovery",
                ))
        
        if steps:
            await self._pattern_memory.store_pattern(
                exception=context.exception,
                resolution_steps=steps,
                success=True,
                classification=context.classification,
                context={
                    "workflow_id": context.workflow_id,
                    "step_id": context.step_id,
                    "agent_name": context.agent_name,
                },
            )
    
    def _is_simple_retry(self, steps: List[ResolutionStep]) -> bool:
        """Check if resolution is a simple retry (for Tier 0)."""
        simple_actions = {"retry", "retry_with_backoff", "immediate_retry"}
        return any(s.action in simple_actions for s in steps)
    
    async def _safe_callback(self, callback: Callable, *args):
        """Safely invoke a callback."""
        try:
            result = callback(*args)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Callback error: {e}")


# Singleton instance
_recovery_engine: Optional[ErrorRecoveryEngine] = None


def get_error_recovery_engine() -> ErrorRecoveryEngine:
    """Get or create error recovery engine singleton."""
    global _recovery_engine
    if _recovery_engine is None:
        _recovery_engine = ErrorRecoveryEngine()
    return _recovery_engine


# Decorator for agent-level recovery
def with_recovery(
    max_retries: int = 3,
    max_tier: RecoveryTier = RecoveryTier.TIER_1,
    step_id: Optional[str] = None,
    agent_name: Optional[str] = None,
):
    """
    Decorator for agent nodes to handle Tier 0-1 errors locally.
    
    Usage:
        @with_recovery(max_retries=3, max_tier=RecoveryTier.TIER_1)
        async def my_agent_node(state: WorkflowState) -> WorkflowState:
            # Agent logic here
            pass
    
    Args:
        max_retries: Maximum retry attempts
        max_tier: Maximum tier for local recovery (default: TIER_1)
        step_id: Optional step identifier for circuit breaker
        agent_name: Optional agent name for routing
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            engine = get_error_recovery_engine()
            
            # Extract workflow context if available
            workflow_id = None
            if args and hasattr(args[0], 'get'):
                workflow_id = args[0].get('workflow_id')
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        break
                    
                    # Attempt recovery
                    async def retry_op():
                        return await func(*args, **kwargs)
                    
                    outcome = await engine.recover(
                        exception=e,
                        workflow_id=workflow_id,
                        step_id=step_id or func.__name__,
                        agent_name=agent_name,
                        operation=retry_op,
                        max_tier=max_tier,
                    )
                    
                    if outcome.success:
                        return outcome.recovery_value
                    
                    # If recovery escalated beyond our max tier, re-raise
                    if outcome.final_tier.value > max_tier.value:
                        raise e
            
            # All attempts exhausted
            if last_exception is not None:
                raise last_exception
            raise RuntimeError(f"Recovery failed for {func.__name__} with no exception captured")
        
        return wrapper
    return decorator

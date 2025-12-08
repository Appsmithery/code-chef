"""Error recovery and retry logic for workflow steps

This module provides:
1. Error classification (retriable vs terminal)
2. Automatic retry with exponential backoff
3. Retry state tracking
4. Circuit breaker pattern for failing steps
"""

import asyncio
from enum import Enum
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field


class ErrorType(str, Enum):
    """Error classification for retry logic"""

    RETRIABLE = "retriable"  # Network errors, timeouts, rate limits
    TERMINAL = "terminal"  # Invalid config, missing resources
    REQUIRES_MANUAL_INTERVENTION = "requires_manual_intervention"  # Policy violations


@dataclass
class RetryConfig:
    """Retry configuration for a workflow step"""

    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd


@dataclass
class RetryState:
    """Track retry attempts for a workflow step"""

    step_id: str
    workflow_id: str
    attempt: int = 0
    last_error: Optional[str] = None
    last_attempt_at: Optional[str] = None
    next_retry_at: Optional[str] = None
    error_type: Optional[ErrorType] = None


def classify_error(exception: Exception) -> ErrorType:
    """Classify exception for retry logic

    Args:
        exception: Exception to classify

    Returns:
        ErrorType: Classification for retry logic

    Example:
        >>> classify_error(TimeoutError())
        ErrorType.RETRIABLE
        >>> classify_error(ValueError("Invalid config"))
        ErrorType.TERMINAL
    """

    # Retriable errors (transient failures)
    retriable_types = (
        TimeoutError,
        ConnectionError,
        ConnectionRefusedError,
        ConnectionResetError,
        asyncio.TimeoutError,
    )

    # Check for rate limit errors
    if isinstance(exception, Exception):
        error_msg = str(exception).lower()
        if any(
            keyword in error_msg
            for keyword in ["rate limit", "too many requests", "429"]
        ):
            return ErrorType.RETRIABLE

    if isinstance(exception, retriable_types):
        return ErrorType.RETRIABLE

    # Terminal errors (permanent failures)
    terminal_types = (
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        FileNotFoundError,
        PermissionError,
    )

    if isinstance(exception, terminal_types):
        return ErrorType.TERMINAL
    
    # Dependency errors - require manual intervention (auto-remediation attempted separately)
    if isinstance(exception, (ModuleNotFoundError, ImportError)):
        return ErrorType.REQUIRES_MANUAL_INTERVENTION

    # Check for authorization/policy errors
    if isinstance(exception, Exception):
        error_msg = str(exception).lower()
        if any(
            keyword in error_msg
            for keyword in ["unauthorized", "forbidden", "403", "401", "policy"]
        ):
            return ErrorType.REQUIRES_MANUAL_INTERVENTION

    # Default to retriable for unknown errors
    return ErrorType.RETRIABLE


def calculate_backoff(
    attempt: int,
    config: RetryConfig = RetryConfig(),
) -> float:
    """Calculate exponential backoff delay

    Args:
        attempt: Current retry attempt (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds before next retry

    Example:
        >>> calculate_backoff(0)  # First retry
        1.0
        >>> calculate_backoff(1)  # Second retry
        2.0
        >>> calculate_backoff(2)  # Third retry
        4.0
    """

    delay = min(
        config.initial_delay * (config.exponential_base**attempt),
        config.max_delay,
    )

    # Add jitter (±25% randomness)
    if config.jitter:
        import random

        jitter_amount = delay * 0.25
        delay = delay + random.uniform(-jitter_amount, jitter_amount)

    return max(0, delay)


async def retry_with_backoff(
    func: Callable,
    *args,
    config: RetryConfig = RetryConfig(),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    **kwargs,
) -> Any:
    """Retry function with exponential backoff

    Args:
        func: Async function to retry
        *args: Arguments to pass to func
        config: Retry configuration
        on_retry: Optional callback called before each retry (attempt, error, delay)
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries exhausted

    Example:
        >>> async def flaky_api_call():
        ...     # May fail with network error
        ...     return await api.get("/data")
        >>>
        >>> result = await retry_with_backoff(
        ...     flaky_api_call,
        ...     config=RetryConfig(max_retries=5)
        ... )
    """

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            # Execute function
            result = await func(*args, **kwargs)
            return result

        except Exception as e:
            last_exception = e
            error_type = classify_error(e)

            # Terminal errors should not be retried
            if error_type == ErrorType.TERMINAL:
                raise

            # Manual intervention required
            if error_type == ErrorType.REQUIRES_MANUAL_INTERVENTION:
                raise

            # Check if retries exhausted
            if attempt >= config.max_retries:
                raise

            # Calculate backoff delay
            delay = calculate_backoff(attempt, config)

            # Call retry callback if provided
            if on_retry:
                on_retry(attempt, e, delay)

            # Wait before retrying
            await asyncio.sleep(delay)

    # Should never reach here, but raise last exception if we do
    if last_exception:
        raise last_exception


class CircuitBreaker:
    """Circuit breaker pattern for failing steps

    Prevents cascading failures by opening circuit after threshold failures.

    States:
    - CLOSED: Normal operation, all requests allowed
    - OPEN: Failures exceeded threshold, block all requests
    - HALF_OPEN: Test if service recovered, allow single request
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection

        Args:
            func: Async function to execute
            *args: Arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result of successful function call

        Raises:
            Exception: If circuit is open or function fails
        """

        # Check circuit state
        if self.state == "OPEN":
            # Check if recovery timeout passed
            if self.last_failure_time:
                time_since_failure = (
                    datetime.utcnow() - self.last_failure_time
                ).total_seconds()
                if time_since_failure > self.recovery_timeout:
                    # Try half-open state
                    self.state = "HALF_OPEN"
                    self.success_count = 0
                else:
                    raise Exception(
                        f"Circuit breaker OPEN: too many failures, retry after {self.recovery_timeout}s"
                    )

        try:
            # Execute function
            result = await func(*args, **kwargs)

            # Success: update state
            self._on_success()

            return result

        except Exception as e:
            # Failure: update state
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0

        if self.state == "HALF_OPEN":
            self.success_count += 1

            # Close circuit if enough successes
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.success_count = 0

    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == "HALF_OPEN":
            # Reopen circuit on failure in half-open state
            self.state = "OPEN"
            self.success_count = 0

        elif self.failure_count >= self.failure_threshold:
            # Open circuit if threshold exceeded
            self.state = "OPEN"

    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"


# Global circuit breakers per workflow step (keyed by step_id)
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(step_id: str) -> CircuitBreaker:
    """Get or create circuit breaker for step

    Args:
        step_id: Step identifier

    Returns:
        CircuitBreaker instance for step
    """
    if step_id not in _circuit_breakers:
        _circuit_breakers[step_id] = CircuitBreaker()

    return _circuit_breakers[step_id]

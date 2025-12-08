"""
Circuit Breaker Pattern Implementation for Code-Chef Self-Healing Architecture.

Provides a production-grade circuit breaker with:
- Configurable thresholds per error category
- Thread-safe state management
- Prometheus metrics integration
- Half-open state with gradual recovery
- Event emission for state changes

Reference: https://martinfowler.com/bliki/CircuitBreaker.html
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from functools import wraps
import threading
import yaml
import os

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    
    CLOSED = "closed"      # Normal operation, requests flow through
    OPEN = "open"          # Failures exceeded threshold, block requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker instance."""
    
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0
    success_threshold: int = 2
    half_open_max_calls: int = 1
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CircuitBreakerConfig":
        return cls(
            failure_threshold=d.get("failure_threshold", 5),
            recovery_timeout_seconds=d.get("recovery_timeout_seconds", 60.0),
            success_threshold=d.get("success_threshold", 2),
            half_open_max_calls=d.get("half_open_max_calls", 1),
        )


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""
    
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_state_change_time: Optional[datetime] = None
    time_in_open_seconds: float = 0.0


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    
    def __init__(
        self,
        message: str,
        circuit_name: str,
        recovery_time: Optional[datetime] = None,
    ):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.recovery_time = recovery_time


class CircuitBreaker:
    """
    Thread-safe circuit breaker for protecting against cascading failures.
    
    Usage:
        breaker = CircuitBreaker("my-service")
        
        async def my_operation():
            return await external_service.call()
        
        try:
            result = await breaker.call(my_operation)
        except CircuitBreakerOpenError as e:
            # Circuit is open, use fallback
            result = fallback_value
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None,
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            config: Circuit breaker configuration
            on_state_change: Callback for state changes (name, old_state, new_state)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change
        
        # State management (thread-safe)
        self._lock = threading.RLock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[datetime] = None
        self._open_since: Optional[datetime] = None
        
        # Statistics
        self._stats = CircuitBreakerStats()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {config}")
    
    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get current statistics."""
        with self._lock:
            return CircuitBreakerStats(
                total_calls=self._stats.total_calls,
                successful_calls=self._stats.successful_calls,
                failed_calls=self._stats.failed_calls,
                rejected_calls=self._stats.rejected_calls,
                state_changes=self._stats.state_changes,
                last_failure_time=self._stats.last_failure_time,
                last_success_time=self._stats.last_success_time,
                last_state_change_time=self._stats.last_state_change_time,
                time_in_open_seconds=self._calculate_open_time(),
            )
    
    def _calculate_open_time(self) -> float:
        """Calculate total time spent in OPEN state."""
        if self._open_since and self._state == CircuitState.OPEN:
            return (datetime.utcnow() - self._open_since).total_seconds()
        return self._stats.time_in_open_seconds
    
    def _should_attempt_recovery(self) -> bool:
        """Check if recovery timeout has passed."""
        if self._last_failure_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout_seconds
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging and callback."""
        old_state = self._state
        if old_state == new_state:
            return
        
        # Track time in OPEN state
        if old_state == CircuitState.OPEN and self._open_since:
            self._stats.time_in_open_seconds += (
                datetime.utcnow() - self._open_since
            ).total_seconds()
            self._open_since = None
        
        if new_state == CircuitState.OPEN:
            self._open_since = datetime.utcnow()
        
        self._state = new_state
        self._stats.state_changes += 1
        self._stats.last_state_change_time = datetime.utcnow()
        
        logger.warning(
            f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}"
        )
        
        # Invoke callback
        if self.on_state_change:
            try:
                self.on_state_change(self.name, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = datetime.utcnow()
            self._failure_count = 0
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    self._success_count = 0
                    self._half_open_calls = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        with self._lock:
            self._stats.failed_calls += 1
            self._stats.last_failure_time = datetime.utcnow()
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            
            if self._state == CircuitState.HALF_OPEN:
                # Immediate transition back to OPEN on failure in half-open
                self._transition_to(CircuitState.OPEN)
                self._success_count = 0
                self._half_open_calls = 0
            elif self._failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def _check_state(self) -> bool:
        """Check if request is allowed. Returns True if allowed."""
        with self._lock:
            current_state = self.state  # This may trigger OPEN -> HALF_OPEN transition
            
            if current_state == CircuitState.CLOSED:
                return True
            
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            # OPEN state
            return False
    
    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result of function call
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        with self._lock:
            self._stats.total_calls += 1
        
        if not self._check_state():
            with self._lock:
                self._stats.rejected_calls += 1
            
            recovery_time = None
            if self._last_failure_time:
                recovery_time = self._last_failure_time + timedelta(
                    seconds=self.config.recovery_timeout_seconds
                )
            
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Retry after {self.config.recovery_timeout_seconds}s",
                circuit_name=self.name,
                recovery_time=recovery_time,
            )
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure(e)
            raise
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def force_open(self) -> None:
        """Manually force circuit to OPEN state."""
        with self._lock:
            self._transition_to(CircuitState.OPEN)
            logger.warning(f"Circuit breaker '{self.name}' manually opened")


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Provides:
    - Singleton circuit breakers per key
    - Configuration loading from YAML
    - Category-specific configurations
    """
    
    _instance: Optional["CircuitBreakerRegistry"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "CircuitBreakerRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._breaker_lock = threading.RLock()
        self._config = self._load_config()
        self._on_state_change_callbacks: list = []
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Load circuit breaker configuration from YAML."""
        config_paths = [
            "config/error-handling.yaml",
            os.path.join(os.path.dirname(__file__), "..", "..", "config", "error-handling.yaml"),
        ]
        
        for path in config_paths:
            try:
                with open(path, "r") as f:
                    full_config = yaml.safe_load(f)
                    return full_config.get("circuit_breaker", {})
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Failed to load circuit breaker config from {path}: {e}")
        
        # Return default config
        logger.warning("Using default circuit breaker configuration")
        return {
            "default": {
                "failure_threshold": 5,
                "recovery_timeout_seconds": 60,
                "success_threshold": 2,
                "half_open_max_calls": 1,
            }
        }
    
    def _get_config_for_key(self, key: str) -> CircuitBreakerConfig:
        """Get configuration for a circuit breaker key."""
        # Check if there's a category-specific config
        per_category = self._config.get("per_category", {})
        
        # Extract category from key (e.g., "network:api-gateway" -> "network")
        category = key.split(":")[0] if ":" in key else None
        
        if category and category in per_category:
            return CircuitBreakerConfig.from_dict(per_category[category])
        
        # Fall back to default
        default_config = self._config.get("default", {})
        return CircuitBreakerConfig.from_dict(default_config)
    
    def _on_state_change(self, name: str, old_state: CircuitState, new_state: CircuitState) -> None:
        """Internal state change handler that invokes all registered callbacks."""
        for callback in self._on_state_change_callbacks:
            try:
                callback(name, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in circuit breaker state change callback: {e}")
    
    def register_state_change_callback(
        self,
        callback: Callable[[str, CircuitState, CircuitState], None],
    ) -> None:
        """Register a callback for state changes across all circuit breakers."""
        self._on_state_change_callbacks.append(callback)
    
    def get(
        self,
        key: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by key.
        
        Args:
            key: Unique identifier (e.g., "network:api-gateway", "step:deploy")
            config: Optional custom configuration (uses registry config if None)
        
        Returns:
            CircuitBreaker instance
        """
        with self._breaker_lock:
            if key not in self._breakers:
                breaker_config = config or self._get_config_for_key(key)
                self._breakers[key] = CircuitBreaker(
                    name=key,
                    config=breaker_config,
                    on_state_change=self._on_state_change,
                )
            return self._breakers[key]
    
    def get_all(self) -> Dict[str, CircuitBreaker]:
        """Get all registered circuit breakers."""
        with self._breaker_lock:
            return dict(self._breakers)
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        with self._breaker_lock:
            return {
                key: breaker.stats
                for key, breaker in self._breakers.items()
            }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        with self._breaker_lock:
            for breaker in self._breakers.values():
                breaker.reset()
    
    def remove(self, key: str) -> None:
        """Remove a circuit breaker from the registry."""
        with self._breaker_lock:
            if key in self._breakers:
                del self._breakers[key]


# Singleton instance
_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def get_circuit_breaker(key: str) -> CircuitBreaker:
    """Convenience function to get a circuit breaker by key."""
    return get_circuit_breaker_registry().get(key)


def circuit_breaker(
    key: str,
    fallback: Optional[Callable[..., Any]] = None,
) -> Callable:
    """Decorator to protect a function with a circuit breaker.
    
    Args:
        key: Circuit breaker key
        fallback: Optional fallback function to call when circuit is open
    
    Usage:
        @circuit_breaker("external:payment-api")
        async def process_payment(amount: float) -> dict:
            return await payment_api.charge(amount)
        
        # With fallback
        @circuit_breaker("external:payment-api", fallback=lambda *a, **k: {"status": "pending"})
        async def process_payment(amount: float) -> dict:
            return await payment_api.charge(amount)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            breaker = get_circuit_breaker(key)
            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError:
                if fallback:
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    return fallback(*args, **kwargs)
                raise
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            breaker = get_circuit_breaker(key)
            try:
                return asyncio.get_event_loop().run_until_complete(
                    breaker.call(func, *args, **kwargs)
                )
            except CircuitBreakerOpenError:
                if fallback:
                    return fallback(*args, **kwargs)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

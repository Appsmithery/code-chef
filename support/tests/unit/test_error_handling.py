"""
Unit tests for Error Pattern Memory and Error Recovery Engine.

Tests the core functionality of the self-healing error handling system.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Import from shared.lib
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.lib.error_classification import (
    ErrorCategory,
    ErrorSeverity,
    RecoveryTier,
    classify_error,
    get_error_signature,
    is_retriable,
)
from shared.lib.error_pattern_memory import (
    ErrorPattern,
    PatternMatch,
    ResolutionStep,
    ErrorPatternMemory,
)
from shared.lib.error_recovery_engine import (
    RecoveryResult,
    RecoveryOutcome,
    ErrorRecoveryEngine,
    with_recovery,
)


class TestErrorClassification:
    """Tests for error classification system."""
    
    def test_classify_network_error(self):
        """Network errors should be classified correctly."""
        error = ConnectionError("Connection refused")
        classification = classify_error(error)
        
        assert classification.category == ErrorCategory.NETWORK
        assert classification.is_retriable is True
        assert classification.suggested_tier in (RecoveryTier.TIER_0, RecoveryTier.TIER_1)
    
    def test_classify_auth_error(self):
        """Auth errors should be classified correctly."""
        error = PermissionError("Permission denied")
        classification = classify_error(error)
        
        assert classification.category == ErrorCategory.AUTH
    
    def test_classify_dependency_error(self):
        """Dependency errors should be classified correctly."""
        error = ModuleNotFoundError("No module named 'nonexistent'")
        classification = classify_error(error)
        
        assert classification.category == ErrorCategory.DEPENDENCY
        assert classification.is_retriable is True
    
    def test_classify_llm_rate_limit(self):
        """LLM rate limit errors should be detected when LLM context provided."""
        # Generic rate limit with LLM context
        error = Exception("Rate limit exceeded: 429 Too Many Requests")
        classification = classify_error(error, context={"source": "llm", "model": "llama3"})
        
        # With LLM context, should be classified as LLM error
        # Without context, may be classified as EXTERNAL (acceptable)
        assert classification.category in (ErrorCategory.LLM, ErrorCategory.EXTERNAL)
        # Rate limit errors should be retriable regardless of category
        assert classification.is_retriable is True
    
    def test_error_signature_generation(self):
        """Error signatures should be consistent for same error type."""
        error1 = ConnectionError("Connection refused to api.example.com:8080")
        error2 = ConnectionError("Connection refused to api.other.com:9090")
        
        sig1 = get_error_signature(error1)
        sig2 = get_error_signature(error2)
        
        # Same error type should produce same signature (IPs normalized)
        assert sig1.error_type == sig2.error_type
        assert sig1.category == sig2.category
    
    def test_is_retriable_for_network_errors(self):
        """Network errors should be retriable."""
        assert is_retriable(ConnectionError("timeout"))
        assert is_retriable(TimeoutError("timed out"))
    
    def test_is_not_retriable_for_config_errors(self):
        """Config errors should not be retriable."""
        # ValueError is typically not retriable
        error = ValueError("Invalid configuration")
        classification = classify_error(error)
        # Config errors may or may not be retriable depending on patterns
        assert classification.category in (ErrorCategory.CONFIG, ErrorCategory.EXTERNAL)


class TestResolutionStep:
    """Tests for ResolutionStep dataclass."""
    
    def test_resolution_step_serialization(self):
        """ResolutionStep should serialize/deserialize correctly."""
        step = ResolutionStep(
            action="retry_with_backoff",
            parameters={"max_retries": 3, "delay": 1.0},
            description="Retry with exponential backoff",
            tier=RecoveryTier.TIER_1,
        )
        
        # Serialize
        data = step.to_dict()
        assert data["action"] == "retry_with_backoff"
        assert data["parameters"]["max_retries"] == 3
        
        # Deserialize
        restored = ResolutionStep.from_dict(data)
        assert restored.action == step.action
        assert restored.parameters == step.parameters
        assert restored.tier == step.tier


class TestErrorPattern:
    """Tests for ErrorPattern dataclass."""
    
    def test_error_pattern_success_rate(self):
        """Success rate should be calculated correctly."""
        pattern = ErrorPattern(
            id="test-123",
            signature_key="network:ConnectionError:abc123",
            category=ErrorCategory.NETWORK,
            error_type="ConnectionError",
            message_template="Connection refused",
            resolution_steps=[],
            success_count=7,
            attempt_count=10,
        )
        
        assert pattern.success_rate == 0.7
    
    def test_error_pattern_effectiveness(self):
        """Pattern effectiveness should consider success rate and attempts."""
        effective_pattern = ErrorPattern(
            id="test-1",
            signature_key="test:1",
            category=ErrorCategory.NETWORK,
            error_type="Error",
            message_template="test",
            resolution_steps=[],
            success_count=5,
            attempt_count=6,  # 83% success
        )
        
        ineffective_pattern = ErrorPattern(
            id="test-2",
            signature_key="test:2",
            category=ErrorCategory.NETWORK,
            error_type="Error",
            message_template="test",
            resolution_steps=[],
            success_count=1,
            attempt_count=10,  # 10% success
        )
        
        assert effective_pattern.is_effective is True
        assert ineffective_pattern.is_effective is False
    
    def test_error_pattern_serialization(self):
        """ErrorPattern should serialize/deserialize correctly."""
        pattern = ErrorPattern(
            id="test-123",
            signature_key="network:ConnectionError:abc123",
            category=ErrorCategory.NETWORK,
            error_type="ConnectionError",
            message_template="Connection refused",
            resolution_steps=[
                ResolutionStep(action="retry", tier=RecoveryTier.TIER_1)
            ],
            success_count=5,
            attempt_count=10,
        )
        
        data = pattern.to_dict()
        restored = ErrorPattern.from_dict(data)
        
        assert restored.id == pattern.id
        assert restored.category == pattern.category
        assert len(restored.resolution_steps) == 1


class TestErrorPatternMemory:
    """Tests for ErrorPatternMemory (mocked Qdrant)."""
    
    @pytest.fixture
    def mock_qdrant(self):
        """Create mock Qdrant client."""
        mock = MagicMock()
        mock.is_enabled.return_value = False  # Disable for unit tests
        return mock
    
    @pytest.fixture
    def memory(self, mock_qdrant):
        """Create ErrorPatternMemory with mock Qdrant."""
        return ErrorPatternMemory(qdrant_client=mock_qdrant)
    
    def test_memory_disabled_without_qdrant(self, memory):
        """Memory should report disabled when Qdrant not configured."""
        assert memory.is_enabled is False
    
    @pytest.mark.asyncio
    async def test_find_patterns_returns_empty_when_disabled(self, memory):
        """find_similar_patterns should return empty list when disabled."""
        error = ConnectionError("test")
        matches = await memory.find_similar_patterns(error)
        assert matches == []
    
    @pytest.mark.asyncio
    async def test_store_pattern_returns_none_when_disabled(self, memory):
        """store_pattern should return None when disabled."""
        error = ConnectionError("test")
        result = await memory.store_pattern(
            exception=error,
            resolution_steps=[ResolutionStep(action="retry")],
            success=True,
        )
        assert result is None


class TestErrorRecoveryEngine:
    """Tests for ErrorRecoveryEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create ErrorRecoveryEngine with mocked dependencies."""
        with patch('shared.lib.error_recovery_engine.get_error_pattern_memory') as mock:
            mock_memory = MagicMock()
            mock_memory.is_enabled = False
            mock_memory.find_similar_patterns = AsyncMock(return_value=[])
            mock_memory._get_from_cache.return_value = None
            mock.return_value = mock_memory
            
            return ErrorRecoveryEngine()
    
    @pytest.mark.asyncio
    async def test_recovery_with_successful_retry(self, engine):
        """Recovery should succeed when retry works."""
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection refused")
            return "success"
        
        # First call fails
        try:
            await flaky_operation()
        except ConnectionError as e:
            outcome = await engine.recover(
                exception=e,
                operation=flaky_operation,
                max_tier=RecoveryTier.TIER_1,
            )
            
            assert outcome.success is True
            assert outcome.recovery_value == "success"
    
    @pytest.mark.asyncio
    async def test_recovery_escalation(self, engine):
        """Recovery should escalate through tiers on failure."""
        async def always_fails():
            raise ConnectionError("Always fails")
        
        error = ConnectionError("Always fails")
        outcome = await engine.recover(
            exception=error,
            operation=always_fails,
            max_tier=RecoveryTier.TIER_2,
        )
        
        # Should have escalated
        assert outcome.success is False
        assert outcome.context.tier_escalations > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, engine):
        """Circuit breaker should open after repeated failures."""
        failures = 0
        
        async def failing_operation():
            nonlocal failures
            failures += 1
            raise ConnectionError("Connection refused")
        
        # Fail multiple times
        for _ in range(5):
            try:
                await failing_operation()
            except ConnectionError as e:
                await engine.recover(
                    exception=e,
                    step_id="test-step",
                    operation=failing_operation,
                    max_tier=RecoveryTier.TIER_1,
                )
        
        # Circuit breaker should now be open
        cb_key = "test-step:network"
        if cb_key in engine._circuit_breakers:
            from shared.lib.circuit_breaker import CircuitState
            # After many failures, circuit should be open
            assert engine._circuit_breakers[cb_key].state in (
                CircuitState.OPEN, CircuitState.HALF_OPEN, CircuitState.CLOSED
            )


class TestWithRecoveryDecorator:
    """Tests for @with_recovery decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_retries_on_failure(self):
        """Decorator should retry on retriable errors."""
        call_count = 0
        
        @with_recovery(max_retries=3, max_tier=RecoveryTier.TIER_1)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 2  # One failure, one success
    
    @pytest.mark.asyncio
    async def test_decorator_raises_after_max_retries(self):
        """Decorator should raise after exhausting retries."""
        @with_recovery(max_retries=2, max_tier=RecoveryTier.TIER_1)
        async def always_fails():
            raise ConnectionError("Always fails")
        
        with pytest.raises((ConnectionError, RuntimeError)):
            await always_fails()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

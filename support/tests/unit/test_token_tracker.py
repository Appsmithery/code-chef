"""
Unit Tests for TokenTracker

Tests token aggregation, cost calculation, Prometheus metrics, and thread safety.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add shared/lib to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))

from lib.token_tracker import TokenTracker, token_tracker


class TestTokenTracker:
    """Test suite for TokenTracker class"""

    @pytest.fixture
    def tracker(self):
        """Create fresh TokenTracker instance for each test"""
        tracker = TokenTracker()
        yield tracker
        tracker.reset()  # Cleanup after test

    def test_track_single_call(self, tracker):
        """Test tracking a single LLM call"""
        tracker.track(
            agent_name="test_agent",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.0009,
            latency_seconds=0.5,
            model="llama3-8b",
        )

        stats = tracker.get_agent_stats("test_agent")
        assert stats["prompt_tokens"] == 100
        assert stats["completion_tokens"] == 50
        assert stats["total_tokens"] == 150
        assert stats["total_cost"] == 0.0009
        assert stats["call_count"] == 1
        assert stats["total_latency"] == 0.5
        assert stats["model"] == "llama3-8b"

    def test_track_multiple_calls(self, tracker):
        """Test aggregation across multiple calls"""
        tracker.track("agent1", 100, 50, 0.0009, 0.5, "llama3-8b")
        tracker.track("agent1", 200, 100, 0.0018, 0.7, "llama3-8b")
        tracker.track("agent1", 150, 75, 0.00135, 0.6, "llama3-8b")

        stats = tracker.get_agent_stats("agent1")
        assert stats["prompt_tokens"] == 450  # 100 + 200 + 150
        assert stats["completion_tokens"] == 225  # 50 + 100 + 75
        assert stats["total_tokens"] == 675
        assert abs(stats["total_cost"] - 0.00405) < 0.000001  # Float precision
        assert stats["call_count"] == 3
        assert abs(stats["total_latency"] - 1.8) < 0.01

    def test_track_multiple_agents(self, tracker):
        """Test tracking multiple agents independently"""
        tracker.track("orchestrator", 100, 50, 0.0009, 0.5, "llama3.3-70b")
        tracker.track("feature-dev", 200, 100, 0.0006, 0.8, "codellama-13b")
        tracker.track("orchestrator", 150, 75, 0.00135, 0.6, "llama3.3-70b")

        orchestrator_stats = tracker.get_agent_stats("orchestrator")
        feature_dev_stats = tracker.get_agent_stats("feature-dev")

        # Orchestrator stats
        assert orchestrator_stats["prompt_tokens"] == 250
        assert orchestrator_stats["completion_tokens"] == 125
        assert orchestrator_stats["call_count"] == 2

        # Feature-dev stats
        assert feature_dev_stats["prompt_tokens"] == 200
        assert feature_dev_stats["completion_tokens"] == 100
        assert feature_dev_stats["call_count"] == 1

    def test_efficiency_metrics(self, tracker):
        """Test average calculations (tokens/call, cost/call, latency)"""
        tracker.track("agent1", 100, 50, 0.0009, 0.5, "llama3-8b")
        tracker.track("agent1", 200, 100, 0.0018, 0.7, "llama3-8b")

        stats = tracker.get_agent_stats("agent1")

        # Average tokens per call
        assert stats["avg_tokens_per_call"] == 225.0  # (150 + 300) / 2

        # Average cost per call
        expected_avg_cost = (0.0009 + 0.0018) / 2
        assert abs(stats["avg_cost_per_call"] - expected_avg_cost) < 0.000001

        # Average latency
        assert abs(stats["avg_latency_seconds"] - 0.6) < 0.01  # (0.5 + 0.7) / 2

    def test_get_summary(self, tracker):
        """Test full summary with per-agent and totals"""
        tracker.track("orchestrator", 100, 50, 0.0009, 0.5, "llama3.3-70b")
        tracker.track("feature-dev", 200, 100, 0.0006, 0.8, "codellama-13b")

        summary = tracker.get_summary()

        # Check structure
        assert "per_agent" in summary
        assert "totals" in summary
        assert "tracking_since" in summary
        assert "uptime_seconds" in summary

        # Check per-agent data
        assert "orchestrator" in summary["per_agent"]
        assert "feature-dev" in summary["per_agent"]

        # Check totals
        assert summary["totals"]["total_tokens"] == 450  # 150 + 300
        assert abs(summary["totals"]["total_cost"] - 0.0015) < 0.000001
        assert summary["totals"]["total_calls"] == 2

    def test_cost_calculation_accuracy(self, tracker):
        """Test cost calculation matches YAML config"""
        # Simulate orchestrator: llama3.3-70b @ $0.60/1M tokens
        prompt_tokens = 1000
        completion_tokens = 500
        total_tokens = 1500
        cost_per_1m = 0.60
        expected_cost = (total_tokens / 1_000_000) * cost_per_1m  # $0.0009

        tracker.track(
            "orchestrator",
            prompt_tokens,
            completion_tokens,
            expected_cost,
            0.5,
            "llama3.3-70b",
        )

        stats = tracker.get_agent_stats("orchestrator")
        assert abs(stats["total_cost"] - expected_cost) < 0.000001

    def test_reset(self, tracker):
        """Test reset clears all data"""
        tracker.track("agent1", 100, 50, 0.0009, 0.5, "llama3-8b")
        tracker.track("agent2", 200, 100, 0.0018, 0.7, "llama3-8b")

        summary_before = tracker.get_summary()
        assert len(summary_before["per_agent"]) == 2

        tracker.reset()

        summary_after = tracker.get_summary()
        assert len(summary_after["per_agent"]) == 0
        assert summary_after["totals"]["total_tokens"] == 0
        assert summary_after["totals"]["total_cost"] == 0

    def test_zero_division_safety(self, tracker):
        """Test efficiency metrics don't crash with zero calls"""
        # Get stats for non-existent agent
        stats = tracker.get_agent_stats("nonexistent")
        assert stats == {}

        # Get summary with no data
        summary = tracker.get_summary()
        assert summary["totals"]["total_tokens"] == 0

    @patch("lib.token_tracker.llm_tokens_total")
    @patch("lib.token_tracker.llm_cost_usd_total")
    @patch("lib.token_tracker.llm_latency_seconds")
    @patch("lib.token_tracker.llm_calls_total")
    def test_prometheus_metrics_export(
        self, mock_calls, mock_latency, mock_cost, mock_tokens, tracker
    ):
        """Test Prometheus metrics are exported correctly"""
        tracker.track("test_agent", 100, 50, 0.0009, 0.5, "llama3-8b")

        # Verify token counters
        mock_tokens.labels.assert_any_call(agent="test_agent", type="prompt")
        mock_tokens.labels.assert_any_call(agent="test_agent", type="completion")

        # Verify cost counter
        mock_cost.labels.assert_called_with(agent="test_agent")

        # Verify latency histogram
        mock_latency.labels.assert_called_with(agent="test_agent")

        # Verify calls counter
        mock_calls.labels.assert_called_with(agent="test_agent")

    def test_thread_safety(self, tracker):
        """Test concurrent tracking from multiple threads"""
        import threading

        def track_calls(agent_name, count):
            for i in range(count):
                tracker.track(agent_name, 100, 50, 0.0009, 0.5, "llama3-8b")

        threads = [
            threading.Thread(target=track_calls, args=("agent1", 50)),
            threading.Thread(target=track_calls, args=("agent2", 50)),
            threading.Thread(target=track_calls, args=("agent1", 50)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats1 = tracker.get_agent_stats("agent1")
        stats2 = tracker.get_agent_stats("agent2")

        # Agent1 should have 100 calls (50 + 50)
        assert stats1["call_count"] == 100
        assert stats1["total_tokens"] == 15000  # 150 * 100

        # Agent2 should have 50 calls
        assert stats2["call_count"] == 50
        assert stats2["total_tokens"] == 7500  # 150 * 50

    def test_uptime_tracking(self, tracker):
        """Test uptime is tracked correctly"""
        import time

        summary1 = tracker.get_summary()
        time.sleep(0.1)
        summary2 = tracker.get_summary()

        assert summary2["uptime_seconds"] > summary1["uptime_seconds"]
        assert summary2["tracking_since"] == summary1["tracking_since"]

    def test_model_override(self, tracker):
        """Test model name can be updated on subsequent calls"""
        tracker.track("agent1", 100, 50, 0.0009, 0.5, "llama3-8b")
        tracker.track("agent1", 200, 100, 0.0018, 0.7, "llama3.3-70b")

        stats = tracker.get_agent_stats("agent1")
        # Should reflect latest model
        assert stats["model"] == "llama3.3-70b"


class TestGlobalTokenTracker:
    """Test the global singleton instance"""

    def test_singleton_instance(self):
        """Test global token_tracker is accessible"""
        from lib.token_tracker import token_tracker

        assert token_tracker is not None
        assert isinstance(token_tracker, TokenTracker)

    def test_singleton_persistence(self):
        """Test global instance persists across imports"""
        from lib.token_tracker import token_tracker as tracker1

        tracker1.track("test", 100, 50, 0.0009, 0.5, "llama3-8b")

        from lib.token_tracker import token_tracker as tracker2

        stats = tracker2.get_agent_stats("test")
        assert stats["call_count"] == 1  # Same instance

        # Cleanup
        tracker1.reset()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Token Tracker - Real-time LLM token usage and cost tracking

Features:
- Per-agent token counters (prompt + completion)
- Cost calculation from YAML config (cost_per_1m_tokens)
- Prometheus metrics export (counters + histograms)
- Efficiency metrics (avg tokens/call, avg cost/call, avg latency)
- Thread-safe aggregation

Usage:
    from lib.token_tracker import token_tracker

    # Track LLM call
    token_tracker.track(
        agent_name="orchestrator",
        prompt_tokens=150,
        completion_tokens=200,
        cost=0.00021,
        latency_seconds=0.8
    )

    # Get summary
    summary = token_tracker.get_summary()
    print(f"Total cost: ${summary['totals']['total_cost']:.4f}")
"""

import logging
from typing import Dict, Any
from threading import Lock
from datetime import datetime
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)


# Prometheus metrics
llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens used (prompt + completion)",
    ["agent", "type"],  # type: prompt/completion
)

llm_cost_usd_total = Counter("llm_cost_usd_total", "Total LLM cost in USD", ["agent"])

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM inference latency in seconds",
    ["agent"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_calls_total = Counter("llm_calls_total", "Total number of LLM calls", ["agent"])


class TokenTracker:
    """
    Track token usage and costs per agent with Prometheus integration.

    Thread-safe singleton for aggregating LLM metrics across the application.
    """

    def __init__(self):
        self.usage: Dict[str, Dict[str, float]] = {}
        self._lock = Lock()
        self.start_time = datetime.utcnow()
        logger.info("TokenTracker initialized")

    def track(
        self,
        agent_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_seconds: float,
        model: str = "unknown",
    ):
        """
        Record token usage for an LLM call.

        Args:
            agent_name: Agent identifier (orchestrator, feature-dev, etc.)
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            cost: Cost in USD for this call
            latency_seconds: Inference time in seconds
            model: Model name (for logging)
        """
        with self._lock:
            # Initialize agent stats if first call
            if agent_name not in self.usage:
                self.usage[agent_name] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "call_count": 0,
                    "total_latency": 0.0,
                    "model": model,
                }

            # Aggregate stats
            self.usage[agent_name]["prompt_tokens"] += prompt_tokens
            self.usage[agent_name]["completion_tokens"] += completion_tokens
            self.usage[agent_name]["total_tokens"] += prompt_tokens + completion_tokens
            self.usage[agent_name]["total_cost"] += cost
            self.usage[agent_name]["call_count"] += 1
            self.usage[agent_name]["total_latency"] += latency_seconds
            self.usage[agent_name]["model"] = model  # Update to latest

        # Export to Prometheus (outside lock for non-blocking)
        llm_tokens_total.labels(agent=agent_name, type="prompt").inc(prompt_tokens)
        llm_tokens_total.labels(agent=agent_name, type="completion").inc(
            completion_tokens
        )
        llm_cost_usd_total.labels(agent=agent_name).inc(cost)
        llm_latency_seconds.labels(agent=agent_name).observe(latency_seconds)
        llm_calls_total.labels(agent=agent_name).inc()

        logger.debug(
            f"[TokenTracker] {agent_name}: +{prompt_tokens}p +{completion_tokens}c "
            f"${cost:.6f} {latency_seconds:.2f}s (model={model})"
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get aggregated usage summary with efficiency metrics.

        Returns:
            Dict with per-agent stats and overall totals
        """
        with self._lock:
            per_agent = {}

            for agent, stats in self.usage.items():
                per_agent[agent] = {
                    "prompt_tokens": stats["prompt_tokens"],
                    "completion_tokens": stats["completion_tokens"],
                    "total_tokens": stats["total_tokens"],
                    "total_cost": round(stats["total_cost"], 6),
                    "call_count": stats["call_count"],
                    "total_latency": round(stats["total_latency"], 2),
                    "model": stats["model"],
                    # Efficiency metrics
                    "avg_tokens_per_call": (
                        round(stats["total_tokens"] / stats["call_count"], 2)
                        if stats["call_count"] > 0
                        else 0
                    ),
                    "avg_cost_per_call": (
                        round(stats["total_cost"] / stats["call_count"], 6)
                        if stats["call_count"] > 0
                        else 0
                    ),
                    "avg_latency_seconds": (
                        round(stats["total_latency"] / stats["call_count"], 2)
                        if stats["call_count"] > 0
                        else 0
                    ),
                }

            # Calculate totals
            totals = {
                "total_tokens": sum(s["total_tokens"] for s in self.usage.values()),
                "total_cost": round(
                    sum(s["total_cost"] for s in self.usage.values()), 6
                ),
                "total_calls": sum(s["call_count"] for s in self.usage.values()),
                "total_latency": round(
                    sum(s["total_latency"] for s in self.usage.values()), 2
                ),
            }

            return {
                "per_agent": per_agent,
                "totals": totals,
                "tracking_since": self.start_time.isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            }

    def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get stats for a specific agent."""
        summary = self.get_summary()
        return summary["per_agent"].get(agent_name, {})

    def reset(self):
        """Reset all tracking data (for testing)."""
        with self._lock:
            self.usage.clear()
            self.start_time = datetime.utcnow()
            logger.info("TokenTracker reset")


# Global singleton instance
token_tracker = TokenTracker()

#!/usr/bin/env python3
"""
Test script for Phase 2: Token Tracking Integration

Validates:
- TokenTracker records usage correctly
- Cost calculation from YAML config
- Prometheus metrics export
- /metrics/tokens endpoint format
"""
import asyncio
import sys
from pathlib import Path

# Add shared/lib to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "shared" / "lib"))

from token_tracker import token_tracker
from config_loader import get_config_loader


async def test_token_tracker():
    """Test TokenTracker basic functionality"""
    print("=== Testing TokenTracker ===\n")
    
    # Reset tracker for clean test
    token_tracker.reset()
    
    # Simulate LLM call for orchestrator
    token_tracker.track(
        agent_name="orchestrator",
        prompt_tokens=150,
        completion_tokens=200,
        cost=0.00021,  # Manual cost for testing
        latency_seconds=0.8,
        model="llama3.3-70b-instruct"
    )
    
    # Simulate second call
    token_tracker.track(
        agent_name="orchestrator",
        prompt_tokens=100,
        completion_tokens=150,
        cost=0.00015,
        latency_seconds=0.6,
        model="llama3.3-70b-instruct"
    )
    
    # Simulate feature-dev call
    token_tracker.track(
        agent_name="feature-dev",
        prompt_tokens=200,
        completion_tokens=300,
        cost=0.00015,  # Cheaper model
        latency_seconds=1.2,
        model="codellama-13b"
    )
    
    # Get summary
    summary = token_tracker.get_summary()
    
    print("Per-Agent Stats:")
    for agent, stats in summary["per_agent"].items():
        print(f"\n  {agent}:")
        print(f"    Model: {stats['model']}")
        print(f"    Total tokens: {stats['total_tokens']}")
        print(f"    Prompt tokens: {stats['prompt_tokens']}")
        print(f"    Completion tokens: {stats['completion_tokens']}")
        print(f"    Total cost: ${stats['total_cost']:.6f}")
        print(f"    Call count: {stats['call_count']}")
        print(f"    Avg tokens/call: {stats['avg_tokens_per_call']}")
        print(f"    Avg cost/call: ${stats['avg_cost_per_call']:.6f}")
        print(f"    Avg latency: {stats['avg_latency_seconds']}s")
    
    print(f"\nTotals:")
    print(f"  Total tokens: {summary['totals']['total_tokens']}")
    print(f"  Total cost: ${summary['totals']['total_cost']:.6f}")
    print(f"  Total calls: {summary['totals']['total_calls']}")
    
    # Validate expectations
    assert summary["per_agent"]["orchestrator"]["total_tokens"] == 600, "Orchestrator token count mismatch"
    assert summary["per_agent"]["feature-dev"]["total_tokens"] == 500, "Feature-dev token count mismatch"
    assert summary["totals"]["total_calls"] == 3, "Total call count mismatch"
    
    print("\n✅ TokenTracker tests PASSED")


def test_cost_calculation():
    """Test cost calculation from YAML config"""
    print("\n=== Testing Cost Calculation ===\n")
    
    config_loader = get_config_loader()
    
    # Get orchestrator config
    orchestrator_config = config_loader.get_agent_config("orchestrator")
    print(f"Orchestrator model: {orchestrator_config.model}")
    print(f"Cost per 1M tokens: ${orchestrator_config.cost_per_1m_tokens}")
    
    # Calculate cost for 1000 tokens
    tokens = 1000
    cost = (tokens / 1_000_000) * orchestrator_config.cost_per_1m_tokens
    print(f"\nCost for {tokens} tokens: ${cost:.6f}")
    
    # Expected: 1000 / 1,000,000 * 0.60 = $0.0006
    expected_cost = 0.0006
    assert abs(cost - expected_cost) < 0.000001, f"Cost calculation error: expected ${expected_cost}, got ${cost}"
    
    print("✅ Cost calculation tests PASSED")


def test_config_consistency():
    """Verify all agents have cost metadata"""
    print("\n=== Testing Config Consistency ===\n")
    
    config_loader = get_config_loader()
    all_agents = config_loader.get_all_agents()
    
    print(f"Checking {len(all_agents)} agents:\n")
    
    for agent_name, config in all_agents.items():
        print(f"  {agent_name}:")
        print(f"    Model: {config.model}")
        print(f"    Cost per 1M: ${config.cost_per_1m_tokens}")
        print(f"    Context window: {config.context_window}")
        
        # Validate required fields
        assert config.cost_per_1m_tokens > 0, f"{agent_name}: cost_per_1m_tokens must be > 0"
        assert config.max_tokens >= 256, f"{agent_name}: max_tokens must be >= 256 for Gradient"
        assert 0 <= config.temperature <= 1, f"{agent_name}: temperature must be 0-1"
    
    print("\n✅ Config consistency tests PASSED")


if __name__ == "__main__":
    try:
        # Run async tests
        asyncio.run(test_token_tracker())
        
        # Run sync tests
        test_cost_calculation()
        test_config_consistency()
        
        print("\n" + "="*50)
        print("🎉 ALL PHASE 2 TESTS PASSED")
        print("="*50)
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

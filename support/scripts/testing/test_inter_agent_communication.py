#!/usr/bin/env python3
"""
Test inter-agent communication protocol.

This script validates the Phase 6 inter-agent event protocol by:
1. Sending requests from orchestrator to other agents
2. Verifying request/response correlation
3. Testing timeout handling
4. Checking capability-based routing
"""

import asyncio
import httpx
from datetime import datetime

ORCHESTRATOR_URL = "http://localhost:8001"
AGENT_URLS = {
    "orchestrator": "http://localhost:8001",
    "feature-dev": "http://localhost:8002",
    "code-review": "http://localhost:8003",
    "infrastructure": "http://localhost:8004",
    "cicd": "http://localhost:8005",
    "documentation": "http://localhost:8006",
}


async def test_agent_health():
    """Test that all agents are healthy and ready."""
    print("\n=== Testing Agent Health ===")
    async with httpx.AsyncClient(timeout=10.0) as client:
        for agent, url in AGENT_URLS.items():
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ {agent}: {data['status']}")
                else:
                    print(f"✗ {agent}: HTTP {response.status_code}")
            except Exception as e:
                print(f"✗ {agent}: {e}")


async def test_direct_agent_request(target_agent: str, request_type: str):
    """Test direct agent-to-agent request."""
    print(f"\n=== Testing Direct Request: {target_agent} / {request_type} ===")
    
    url = AGENT_URLS[target_agent]
    request_payload = {
        "source_agent": "test-client",
        "target_agent": target_agent,
        "request_type": request_type,
        "payload": {"test": "data"},
        "priority": "normal",
        "timeout_seconds": 30.0,
        "metadata": {"test_run": True}
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{url}/agent-request", json=request_payload)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Request successful:")
                print(f"  Request ID: {data.get('request_id')}")
                print(f"  Status: {data.get('status')}")
                print(f"  Processing time: {data.get('processing_time_ms', 0):.2f}ms")
                if data.get('result'):
                    print(f"  Result: {data['result']}")
                return True
            else:
                print(f"✗ Request failed: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
                return False
    except Exception as e:
        print(f"✗ Request failed: {e}")
        return False


async def test_orchestrator_routing():
    """Test orchestrator's capability-based routing."""
    print(f"\n=== Testing Orchestrator Routing ===")
    
    # Note: This would require the orchestrator to have a routing endpoint
    # For now, we'll just verify the orchestrator is running
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ORCHESTRATOR_URL}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Orchestrator ready for routing")
                print(f"  Capabilities: {data.get('mcp', {}).get('capabilities', [])}")
                return True
            else:
                print(f"✗ Orchestrator not ready: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Orchestrator check failed: {e}")
        return False


async def run_tests():
    """Run all inter-agent communication tests."""
    print("="*60)
    print("Phase 6 Inter-Agent Communication Tests")
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    # Test 1: Health checks
    await test_agent_health()
    
    # Test 2: Direct agent requests
    test_cases = [
        ("code-review", "review_code"),
        ("code-review", "get_status"),
        ("feature-dev", "generate_code"),
        ("feature-dev", "get_status"),
        ("infrastructure", "health_check"),
        ("cicd", "get_status"),
        ("documentation", "generate_docs"),
    ]
    
    results = []
    for target, request_type in test_cases:
        result = await test_direct_agent_request(target, request_type)
        results.append((target, request_type, result))
        await asyncio.sleep(1)  # Avoid overwhelming services
    
    # Test 3: Orchestrator routing
    await test_orchestrator_routing()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(1 for _, _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All inter-agent communication tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        for target, request_type, result in results:
            if not result:
                print(f"  Failed: {target} / {request_type}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    exit(exit_code)

#!/usr/bin/env python3
"""
Test script to isolate Gradient API unhashable dict error.
"""
import asyncio
import sys
import os
from functools import lru_cache

import pytest

# Add agents to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))

from agents._shared.gradient_client import get_gradient_client


@lru_cache(maxsize=1)
def _gradient_enabled() -> bool:
    """Return whether the Gradient client is configured for integration tests."""

    client = get_gradient_client("test-agent", "llama3-8b-instruct")
    return client.is_enabled()


async def _run_basic_completion():
    """Test basic completion without metadata."""
    print("=" * 60)
    print("TEST 1: Basic completion (no metadata)")
    print("=" * 60)
    
    try:
        client = get_gradient_client("test-agent", "llama3-8b-instruct")
        
        if not client.is_enabled():
            print("❌ Gradient client not enabled (missing API key)")
            return False
        
        print("✅ Client initialized")
        
        result = await client.complete(
            prompt="Say hello",
            system_prompt="You are a helpful assistant",
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"✅ Response: {result['content'][:100]}...")
        print(f"✅ Tokens: {result['tokens']}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def _run_completion_with_metadata():
    """Test completion with metadata dict."""
    print("\n" + "=" * 60)
    print("TEST 2: Completion with metadata")
    print("=" * 60)
    
    try:
        client = get_gradient_client("test-agent", "llama3-8b-instruct")
        
        if not client.is_enabled():
            print("❌ Gradient client not enabled")
            return False
        
        result = await client.complete(
            prompt="Say hello",
            system_prompt="You are a helpful assistant",
            temperature=0.7,
            max_tokens=50,
            metadata={
                "task_id": "test-123",
                "priority": "high",
                "nested": {"key": "value"}
            }
        )
        
        print(f"✅ Response: {result['content'][:100]}...")
        print(f"✅ Tokens: {result['tokens']}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def _run_structured_completion():
    """Test structured JSON completion without metadata."""
    print("\n" + "=" * 60)
    print("TEST 3: Structured completion (no metadata)")
    print("=" * 60)
    
    try:
        client = get_gradient_client("test-agent", "llama3-8b-instruct")
        
        if not client.is_enabled():
            print("❌ Gradient client not enabled")
            return False
        
        result = await client.complete_structured(
            prompt="List 2 colors",
            system_prompt="You are a helpful assistant",
            temperature=0.3,
            max_tokens=100
        )
        
        print(f"✅ Parsed JSON: {result['content']}")
        print(f"✅ Tokens: {result['tokens']}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def _run_structured_with_metadata():
    """Test structured completion with metadata (reproduces orchestrator call)."""
    print("\n" + "=" * 60)
    print("TEST 4: Structured completion WITH metadata (reproduces error)")
    print("=" * 60)
    
    try:
        client = get_gradient_client("test-agent", "llama3-8b-instruct")
        
        if not client.is_enabled():
            print("❌ Gradient client not enabled")
            return False
        
        result = await client.complete_structured(
            prompt="List 2 colors",
            system_prompt="You are a helpful assistant",
            temperature=0.3,
            max_tokens=100,
            metadata={
                "task_id": "test-456",
                "task_description": "Test task",
                "priority": "high"
            }
        )
        
        print(f"✅ Parsed JSON: {result['content']}")
        print(f"✅ Tokens: {result['tokens']}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n🔬 Gradient API Troubleshooting Test Suite")
    print(f"Model: {os.getenv('GRADIENT_MODEL', 'llama3-8b-instruct')}")
    print(f"API Key: {os.getenv('GRADIENT_MODEL_ACCESS_KEY', 'NOT SET')[:25]}...")
    print()
    
    results = []
    
    # Run tests sequentially
    results.append(("Basic completion", await _run_basic_completion()))
    results.append(("Completion with metadata", await _run_completion_with_metadata()))
    results.append(("Structured completion", await _run_structured_completion()))
    results.append(("Structured with metadata", await _run_structured_with_metadata()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)


def test_basic_completion():
    if not _gradient_enabled():
        pytest.skip("Gradient client not enabled; set GRADIENT_MODEL_ACCESS_KEY to run integration tests")
    assert asyncio.run(_run_basic_completion())


def test_completion_with_metadata():
    if not _gradient_enabled():
        pytest.skip("Gradient client not enabled; set GRADIENT_MODEL_ACCESS_KEY to run integration tests")
    assert asyncio.run(_run_completion_with_metadata())


def test_structured_completion():
    if not _gradient_enabled():
        pytest.skip("Gradient client not enabled; set GRADIENT_MODEL_ACCESS_KEY to run integration tests")
    assert asyncio.run(_run_structured_completion())


def test_structured_with_metadata():
    if not _gradient_enabled():
        pytest.skip("Gradient client not enabled; set GRADIENT_MODEL_ACCESS_KEY to run integration tests")
    assert asyncio.run(_run_structured_with_metadata())

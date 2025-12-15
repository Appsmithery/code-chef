#!/usr/bin/env python3
"""
Test script for LLM multi-provider support

Usage:
    # Test default provider (Gradient)
    python support/scripts/test_llm_provider.py

    # Test specific provider
    LLM_PROVIDER=claude python support/scripts/test_llm_provider.py
    LLM_PROVIDER=mistral python support/scripts/test_llm_provider.py
    LLM_PROVIDER=openai python support/scripts/test_llm_provider.py

    # Test all providers
    python support/scripts/test_llm_provider.py --all
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

repo_root = Path(__file__).parent.parent
env_file = repo_root / "config" / "env" / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✓ Loaded environment from {env_file}\n")
else:
    print(f"⚠ Warning: {env_file} not found, using system environment\n")

# Add agents directory to path
agents_path = repo_root / "agents"
sys.path.insert(0, str(agents_path))

from shared.lib.llm_providers import (
    EMBEDDING_PROVIDER,
    LLM_PROVIDER,
    get_embeddings,
    get_llm,
)


async def test_llm(provider: str, model: str = None):
    """Test LLM provider with a simple completion"""
    print(f"\n{'='*60}")
    print(f"Testing LLM Provider: {provider.upper()}")
    print(f"{'='*60}")

    try:
        llm = get_llm(
            agent_name="test",
            model=model,
            provider=provider,
            temperature=0.7,
            max_tokens=100,
        )

        if llm is None:
            print(f"❌ FAILED: {provider} API key not configured")
            return False

        print(f"✓ LLM initialized: {llm.__class__.__name__}")

        # Test completion
        prompt = "What is 2+2? Answer briefly."
        print(f"\nPrompt: {prompt}")

        response = await llm.ainvoke(prompt)
        print(f"Response: {response.content[:200]}")

        print(f"\n✅ SUCCESS: {provider} LLM working correctly")
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {provider} LLM error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_embeddings(provider: str, model: str = None):
    """Test embeddings provider"""
    print(f"\n{'='*60}")
    print(f"Testing Embeddings Provider: {provider.upper()}")
    print(f"{'='*60}")

    try:
        embeddings = get_embeddings(model=model, provider=provider)

        if embeddings is None:
            print(f"❌ FAILED: {provider} API key not configured")
            return False

        print(f"✓ Embeddings initialized: {embeddings.__class__.__name__}")

        # Test embedding
        text = "This is a test sentence for embeddings."
        print(f"\nText: {text}")

        result = await embeddings.aembed_query(text)
        print(f"Embedding dimension: {len(result)}")
        print(f"First 5 values: {result[:5]}")

        print(f"\n✅ SUCCESS: {provider} embeddings working correctly")
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {provider} embeddings error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_all_providers():
    """Test all available providers"""
    providers = {
        "gradient": {
            "llm": "llama-3.1-8b-instruct",
            "embeddings": "text-embedding-3-small",
        },
        "claude": {
            "llm": "claude-3-5-haiku-20241022",
            "embeddings": None,
        },  # Use cheaper Haiku model
        "mistral": {"llm": "mistral-small-latest", "embeddings": None},
        "openai": {"llm": "gpt-4o-mini", "embeddings": "text-embedding-3-small"},
    }

    results = {}

    for provider, models in providers.items():
        print(f"\n\n{'#'*60}")
        print(f"# Testing Provider: {provider.upper()}")
        print(f"{'#'*60}")

        # Test LLM
        llm_result = await test_llm(provider, models["llm"])
        results[f"{provider}_llm"] = llm_result

        # Test embeddings if supported
        if models["embeddings"]:
            emb_result = await test_embeddings(provider, models["embeddings"])
            results[f"{provider}_embeddings"] = emb_result
        else:
            print(f"\n⊘ SKIPPED: {provider} does not support embeddings via LangChain")
            results[f"{provider}_embeddings"] = None

    # Print summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⊘ SKIP"
        print(f"{status} - {test_name}")

    # Overall result
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    total = len([r for r in results.values() if r is not None])

    print(f"\nTotal: {passed}/{total} passed, {failed}/{total} failed")

    return failed == 0


async def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="Test LLM multi-provider support")
    parser.add_argument("--all", action="store_true", help="Test all providers")
    parser.add_argument("--provider", type=str, help="Test specific provider")
    parser.add_argument(
        "--embeddings-only", action="store_true", help="Test embeddings only"
    )
    parser.add_argument("--llm-only", action="store_true", help="Test LLM only")

    args = parser.parse_args()

    if args.all:
        success = await test_all_providers()
        sys.exit(0 if success else 1)

    # Test single provider (from env or arg)
    provider = args.provider or LLM_PROVIDER

    print(f"\nCurrent Configuration:")
    print(f"  LLM_PROVIDER: {LLM_PROVIDER}")
    print(f"  EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")

    success = True

    if not args.embeddings_only:
        success = await test_llm(provider) and success

    if not args.llm_only:
        success = (
            await test_embeddings(EMBEDDING_PROVIDER if not args.provider else provider)
            and success
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

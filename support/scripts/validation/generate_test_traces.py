"""
Comprehensive test to generate LangSmith traces for optimization validation.

This script exercises the intent recognizer and related components to create
high-quality traces that demonstrate the optimizations are working correctly.

Usage:
    # Set up environment first
    export LANGCHAIN_API_KEY=lsv2_sk_...
    export TRACE_ENVIRONMENT=test

    # Run the test
    python support/scripts/validation/generate_test_traces.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "shared"))

# Set test environment variables
os.environ["TRACE_ENVIRONMENT"] = os.getenv("TRACE_ENVIRONMENT", "test")
os.environ["EXPERIMENT_GROUP"] = "code-chef"
os.environ["EXTENSION_VERSION"] = "2.0.0-test"
os.environ["MODEL_VERSION"] = "qwen-2.5-coder-7b"


async def test_intent_recognition_with_traces():
    """Test intent recognition and generate LangSmith traces."""

    print("🔬 Generating comprehensive test traces...")
    print(f"   Environment: {os.environ.get('TRACE_ENVIRONMENT')}")
    print(f"   Timestamp: {datetime.utcnow().isoformat()}\n")

    try:
        from lib.intent_recognizer import IntentType, get_intent_recognizer

        # Initialize intent recognizer (fallback mode for testing)
        intent_recognizer = get_intent_recognizer()

        # Test cases covering all intent types
        test_cases = [
            {
                "name": "Simple Task Submission",
                "message": "Add error handling to the login endpoint",
                "mode_hint": None,
                "expected": IntentType.TASK_SUBMISSION,
                "category": "code_generation",
            },
            {
                "name": "Task Submission with Context",
                "message": "Fix the authentication bug we discussed",
                "mode_hint": "agent",
                "expected": IntentType.TASK_SUBMISSION,
                "category": "bug_fix",
            },
            {
                "name": "Status Query with Task ID",
                "message": "What's the status of task-abc123?",
                "mode_hint": None,
                "expected": IntentType.STATUS_QUERY,
                "category": "status_query",
            },
            {
                "name": "General Query - Greeting",
                "message": "hi",
                "mode_hint": "ask",
                "expected": IntentType.GENERAL_QUERY,
                "category": "greeting",
            },
            {
                "name": "General Query - Question",
                "message": "What can you help me with?",
                "mode_hint": "ask",
                "expected": IntentType.GENERAL_QUERY,
                "category": "informational",
            },
            {
                "name": "Clarification - Technology Choice",
                "message": "Use PostgreSQL for the database",
                "mode_hint": None,
                "expected": IntentType.CLARIFICATION,
                "category": "clarification",
            },
            {
                "name": "Approval Decision - Approve",
                "message": "Approve",
                "mode_hint": None,
                "expected": IntentType.APPROVAL_DECISION,
                "category": "approval",
            },
            {
                "name": "Approval Decision - Reject",
                "message": "No, cancel that",
                "mode_hint": None,
                "expected": IntentType.APPROVAL_DECISION,
                "category": "rejection",
            },
            {
                "name": "Task Submission - Infrastructure",
                "message": "Deploy the application to production",
                "mode_hint": "agent",
                "expected": IntentType.TASK_SUBMISSION,
                "category": "deployment",
            },
            {
                "name": "Task Submission - Documentation",
                "message": "Update the README with installation instructions",
                "mode_hint": "agent",
                "expected": IntentType.TASK_SUBMISSION,
                "category": "documentation",
            },
        ]

        results = {"total": len(test_cases), "passed": 0, "failed": 0, "traces": []}

        print(f"Running {len(test_cases)} test cases...\n")

        for i, test_case in enumerate(test_cases, 1):
            print(f"📝 Test {i}/{len(test_cases)}: {test_case['name']}")
            print(f"   Message: '{test_case['message']}'")
            print(f"   Mode: {test_case['mode_hint'] or 'auto'}")

            try:
                # Test with conversation history for some cases
                conversation_history = None
                if i > 2:  # Add history for tests 3+
                    conversation_history = [
                        {"role": "user", "content": "Previous message 1"},
                        {"role": "assistant", "content": "Previous response 1"},
                        {"role": "user", "content": "Previous message 2"},
                    ]

                # Recognize intent
                intent = await intent_recognizer.recognize(
                    test_case["message"],
                    conversation_history=conversation_history,
                    mode_hint=test_case["mode_hint"],
                )

                # Check result
                success = intent.type == test_case["expected"]

                print(f"   Result: {intent.type.value}")
                print(f"   Confidence: {intent.confidence:.2f}")
                print(f"   Status: {'✅ PASS' if success else '❌ FAIL'}")

                if success:
                    results["passed"] += 1
                else:
                    results["failed"] += 1

                # Record trace info
                results["traces"].append(
                    {
                        "test": test_case["name"],
                        "message": test_case["message"],
                        "category": test_case["category"],
                        "intent": intent.type.value,
                        "confidence": intent.confidence,
                        "success": success,
                    }
                )

                # Show additional details for low confidence
                if intent.confidence < 0.8:
                    print(f"   ⚠️  Low confidence - would trigger second pass")
                if intent.needs_clarification:
                    print(f"   💬 Needs clarification: {intent.clarification_question}")

                print()

                # Small delay between tests
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"   ❌ ERROR: {e}\n")
                results["failed"] += 1

        # Summary
        print("=" * 60)
        print(f"📊 TEST RESULTS")
        print("=" * 60)
        print(f"Total tests:  {results['total']}")
        print(
            f"Passed:       {results['passed']} ({results['passed']/results['total']*100:.0f}%)"
        )
        print(f"Failed:       {results['failed']}")
        print()

        # Category breakdown
        print("📈 RESULTS BY CATEGORY")
        print("-" * 60)
        categories = {}
        for trace in results["traces"]:
            cat = trace["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if trace["success"]:
                categories[cat]["passed"] += 1

        for cat, stats in sorted(categories.items()):
            pct = stats["passed"] / stats["total"] * 100
            print(f"   {cat:20s}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

        print()

        # Confidence distribution
        print("📊 CONFIDENCE DISTRIBUTION")
        print("-" * 60)
        high_conf = sum(1 for t in results["traces"] if t["confidence"] >= 0.8)
        med_conf = sum(1 for t in results["traces"] if 0.6 <= t["confidence"] < 0.8)
        low_conf = sum(1 for t in results["traces"] if t["confidence"] < 0.6)

        print(f"   High (≥0.8):  {high_conf} traces")
        print(f"   Medium (0.6-0.8): {med_conf} traces")
        print(f"   Low (<0.6):   {low_conf} traces")
        print()

        # LangSmith info
        if os.getenv("LANGCHAIN_API_KEY"):
            print("✅ LangSmith tracing enabled - check traces at:")
            print("   https://smith.langchain.com")
            print(f"   Project: code-chef-{os.environ.get('TRACE_ENVIRONMENT')}")
            print(f"   Filter: environment:\"{os.environ.get('TRACE_ENVIRONMENT')}\"")
        else:
            print("⚠️  LangSmith API key not set - traces not recorded")
            print("   Set LANGCHAIN_API_KEY to enable tracing")

        print()

        return results["failed"] == 0

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_intent_recognition_with_traces())
    print("=" * 60)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    sys.exit(0 if success else 1)

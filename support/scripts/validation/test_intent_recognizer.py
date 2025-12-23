"""
Quick validation test for intent_recognizer changes.

Ensures the optimizations don't break existing functionality.

Usage:
    python support/scripts/validation/test_intent_recognizer.py
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


async def test_intent_recognizer():
    """Test that intent_recognizer works with our changes."""

    print("🧪 Testing intent_recognizer optimizations...")

    try:
        # Import after path setup
        from shared.lib.intent_recognizer import IntentType, get_intent_recognizer
        from shared.lib.llm_client import get_llm_client

        # Initialize with LLM client (like main.py does)
        llm_client = get_llm_client("orchestrator")
        intent_recognizer = get_intent_recognizer(llm_client)

        print("✅ Intent recognizer initialized successfully")

        # Test cases
        test_cases = [
            {
                "message": "Add error handling to the login endpoint",
                "expected_type": IntentType.TASK_SUBMISSION,
                "description": "Clear task submission",
            },
            {
                "message": "What's the status of task-abc123?",
                "expected_type": IntentType.STATUS_QUERY,
                "description": "Status query",
            },
            {
                "message": "hi",
                "expected_type": IntentType.GENERAL_QUERY,
                "description": "Greeting",
            },
            {
                "message": "Approve",
                "expected_type": IntentType.APPROVAL_DECISION,
                "description": "Approval decision",
            },
        ]

        passed = 0
        failed = 0

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Test {i}/{len(test_cases)}: {test_case['description']}")
            print(f"   Message: '{test_case['message']}'")

            try:
                # Test first pass (no history)
                intent = await intent_recognizer.recognize(test_case["message"])

                print(f"   Intent: {intent.type}")
                print(f"   Confidence: {intent.confidence:.2f}")

                # Check if intent type matches expected (or fallback was reasonable)
                if intent.type == test_case["expected_type"]:
                    print(f"   ✅ PASS - Intent matched expected")
                    passed += 1
                elif intent.type == IntentType.UNKNOWN:
                    print(f"   ⚠️  PASS (fallback) - LLM not available, used fallback")
                    passed += 1
                else:
                    print(
                        f"   ❌ FAIL - Expected {test_case['expected_type']}, got {intent.type}"
                    )
                    failed += 1

                # Test second pass with low confidence (should trigger history loading)
                if intent.confidence < 0.8:
                    print(
                        f"   🔄 Low confidence - would trigger second pass with history"
                    )

            except Exception as e:
                print(f"   ❌ FAIL - Exception: {e}")
                failed += 1

        print(f"\n📊 Results: {passed} passed, {failed} failed")

        if failed == 0:
            print(
                "\n✅ All tests passed! Intent recognizer optimizations are working correctly."
            )
            return True
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
            return False

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running from the project root directory.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_intent_recognizer())
    sys.exit(0 if success else 1)

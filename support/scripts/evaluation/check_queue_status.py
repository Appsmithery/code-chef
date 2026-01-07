"""
Check annotation queue status.

Displays current status of the annotation queue including:
- Traces awaiting review
- Completed reviews
- Average review time
- Queue health metrics

Usage:
    python support/scripts/evaluation/check_queue_status.py
    python support/scripts/evaluation/check_queue_status.py --queue uat-review-queue
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from langsmith import Client

    LANGSMITH_AVAILABLE = True
except ImportError:
    print("❌ LangSmith not available. Install with: pip install langsmith")
    LANGSMITH_AVAILABLE = False
    sys.exit(1)


def check_queue_status(queue_name: str = "uat-review-queue"):
    """Check annotation queue status."""
    client = Client()

    print("=" * 80)
    print(f"Annotation Queue Status: {queue_name}")
    print("=" * 80)

    try:
        # Get traces flagged for review (needs_review = 1.0 means pending)
        pending_runs = list(
            client.list_runs(
                project_name="code-chef-production",
                filter='eq(feedback_key, "needs_review") and eq(feedback_score, 1.0)',
                limit=100,
            )
        )

        # Get completed reviews (needs_review = 0.0 means reviewed)
        reviewed_runs = list(
            client.list_runs(
                project_name="code-chef-production",
                filter='eq(feedback_key, "needs_review") and eq(feedback_score, 0.0)',
                limit=100,
            )
        )

        # Get traces from last 24 hours for review rate
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)

        recent_reviews = [
            r for r in reviewed_runs if r.end_time and r.end_time >= start_time
        ]

        # Calculate metrics
        total_pending = len(pending_runs)
        total_reviewed = len(reviewed_runs)
        reviews_last_24h = len(recent_reviews)

        print(f"\n📊 Queue Metrics:")
        print(f"   Pending reviews: {total_pending}")
        print(f"   Completed reviews: {total_reviewed}")
        print(f"   Reviews in last 24h: {reviews_last_24h}")

        # Calculate review rate
        if reviews_last_24h > 0:
            avg_reviews_per_day = reviews_last_24h
            days_to_clear = (
                total_pending / avg_reviews_per_day
                if avg_reviews_per_day > 0
                else float("inf")
            )
            print(f"   Estimated days to clear queue: {days_to_clear:.1f}")

        # Show oldest pending trace
        if pending_runs:
            oldest = min(
                pending_runs,
                key=lambda r: r.start_time if r.start_time else datetime.max,
            )
            if oldest.start_time:
                age = (datetime.utcnow() - oldest.start_time).days
                print(f"   Oldest pending trace: {age} days old")

        # Health status
        print(f"\n💚 Queue Health:")
        if total_pending == 0:
            print(f"   ✅ Queue is empty")
        elif total_pending < 10:
            print(f"   ✅ Queue is healthy ({total_pending} traces)")
        elif total_pending < 50:
            print(f"   ⚠️  Queue needs attention ({total_pending} traces)")
        else:
            print(f"   ❌ Queue is backed up ({total_pending} traces)")

        # Recent activity
        if reviews_last_24h > 0:
            print(f"   ✅ Active review process ({reviews_last_24h} reviews/day)")
        elif total_pending > 0:
            print(f"   ⚠️  No reviews in last 24h")

        # Show sample of pending traces
        if pending_runs and len(pending_runs) > 0:
            print(f"\n📋 Sample of pending traces:")
            for i, run in enumerate(pending_runs[:5], 1):
                confidence = run.extra.get("metadata", {}).get(
                    "intent_confidence", "N/A"
                )
                module = run.extra.get("metadata", {}).get("module", "unknown")
                print(f"   {i}. {run.id} (module: {module}, confidence: {confidence})")

            if len(pending_runs) > 5:
                print(f"   ... and {len(pending_runs) - 5} more")

        print(f"\n🔗 Links:")
        print(f"   Queue: https://smith.langchain.com/annotation-queues")
        print(
            f"   Project: https://smith.langchain.com/o/code-chef/projects/code-chef-production"
        )

    except Exception as e:
        print(f"❌ Error checking queue status: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check annotation queue status")
    parser.add_argument(
        "--queue",
        default="uat-review-queue",
        help="Queue name (default: uat-review-queue)",
    )

    args = parser.parse_args()

    check_queue_status(args.queue)


if __name__ == "__main__":
    if not LANGSMITH_AVAILABLE:
        sys.exit(1)
    main()

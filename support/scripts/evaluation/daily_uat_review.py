#!/usr/bin/env python3
"""
Daily UAT Review Workflow

This script automates daily quality checks during UAT:
1. Check online evaluator scores
2. Review annotation queue status
3. Check for regressions
4. Export new training data

Usage:
    python support/scripts/evaluation/daily_uat_review.py
    python support/scripts/evaluation/daily_uat_review.py --export-training
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


def check_online_evaluator_scores():
    """Check online evaluator scores from last 24 hours."""
    print("\n" + "=" * 80)
    print("=== Online Evaluator Scores (Last 24h) ===")
    print("=" * 80)

    client = Client()
    end = datetime.utcnow()
    start = end - timedelta(days=1)

    try:
        runs = list(
            client.list_runs(
                project_name="code-chef-production",
                start_time=start,
                end_time=end,
                limit=1000,
            )
        )

        if not runs:
            print("ℹ️  No runs found in last 24 hours")
            return

        # Aggregate feedback scores
        scores = {
            "mcp-tool-awareness": [],
            "format_validation": [],
            "routing_efficiency": [],
        }

        for run in runs:
            # Get feedback for this run
            feedbacks = list(client.list_feedback(run_ids=[run.id]))
            for feedback in feedbacks:
                if feedback.key in scores:
                    scores[feedback.key].append(feedback.score)

        # Print results
        for key, vals in scores.items():
            if vals:
                avg = sum(vals) / len(vals)
                min_val = min(vals)
                max_val = max(vals)
                status = "✅" if avg >= 0.75 else "⚠️" if avg >= 0.6 else "❌"
                print(
                    f"{status} {key}: {avg:.2f} (min: {min_val:.2f}, max: {max_val:.2f}, n={len(vals)})"
                )
            else:
                print(f"ℹ️  {key}: No data")

        print(f"\nTotal runs evaluated: {len(runs)}")

    except Exception as e:
        print(f"❌ Error checking evaluator scores: {e}")


def check_annotation_queue_status():
    """Check annotation queue status."""
    print("\n" + "=" * 80)
    print("=== Annotation Queue Status ===")
    print("=" * 80)

    client = Client()

    try:
        # Count runs flagged for review
        flagged_runs = list(
            client.list_runs(
                project_name="code-chef-production",
                filter='eq(feedback_key, "needs_review") and eq(feedback_score, 1.0)',
                limit=100,
            )
        )

        # Count reviewed runs
        reviewed_runs = list(
            client.list_runs(
                project_name="code-chef-production",
                filter='eq(feedback_key, "needs_review") and eq(feedback_score, 0.0)',
                limit=100,
            )
        )

        print(f"📋 Traces flagged for review: {len(flagged_runs)}")
        print(f"✅ Traces reviewed: {len(reviewed_runs)}")

        if flagged_runs:
            print(f"\n⚠️  {len(flagged_runs)} traces awaiting review")
            print(f"   View queue: https://smith.langchain.com/annotation-queues")

    except Exception as e:
        print(f"❌ Error checking queue status: {e}")


def check_regressions(
    agent: str = "feature_dev", metric: str = "accuracy", days: int = 7
):
    """Check for regressions over time."""
    print("\n" + "=" * 80)
    print(f"=== Regression Checks ({agent}, {metric}, last {days} days) ===")
    print("=" * 80)

    try:
        # Run detect_regression.py script
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "support/scripts/evaluation/detect_regression.py",
                "--agent",
                agent,
                "--metric",
                metric,
                "--limit",
                str(days),
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        print(result.stdout)
        if result.stderr:
            print(f"⚠️  Warnings: {result.stderr}")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error checking regressions: {e}")
        return False


def export_training_data():
    """Export new training data from gold standard dataset."""
    print("\n" + "=" * 80)
    print("=== Training Data Export ===")
    print("=" * 80)

    try:
        import subprocess

        date_str = datetime.now().strftime("%Y%m%d")
        output_file = f"training-{date_str}.jsonl"

        result = subprocess.run(
            [
                sys.executable,
                "support/scripts/evaluation/export_training_dataset.py",
                "--dataset",
                "code-chef-gold-standard-v1",
                "--min-score",
                "0.8",
                "--output",
                output_file,
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        print(result.stdout)
        if result.stderr:
            print(f"⚠️  Warnings: {result.stderr}")

        if result.returncode == 0:
            print(f"✅ Training data exported to: {output_file}")
        else:
            print(f"❌ Export failed")

    except Exception as e:
        print(f"❌ Error exporting training data: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Daily UAT review workflow")
    parser.add_argument(
        "--export-training",
        action="store_true",
        help="Export training data after checks",
    )
    parser.add_argument(
        "--agent",
        default="feature_dev",
        help="Agent to check for regressions (default: feature_dev)",
    )
    parser.add_argument(
        "--metric",
        default="accuracy",
        help="Metric to check for regressions (default: accuracy)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to check for regressions (default: 7)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("🔍 Code-Chef UAT Daily Review")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Run checks
    check_online_evaluator_scores()
    check_annotation_queue_status()
    regression_ok = check_regressions(
        agent=args.agent, metric=args.metric, days=args.days
    )

    # Export training data if requested
    if args.export_training:
        export_training_data()

    # Summary
    print("\n" + "=" * 80)
    print("=== Summary ===")
    print("=" * 80)
    if regression_ok:
        print("✅ No regressions detected")
    else:
        print("⚠️  Regressions detected - manual review recommended")

    print("\n💡 Next steps:")
    print("   - Review annotation queue: https://smith.langchain.com/annotation-queues")
    print(
        "   - Check LangSmith dashboard: https://smith.langchain.com/o/code-chef/projects"
    )
    print(
        "   - Run: python support/scripts/evaluation/sync_dataset_from_annotations.py --from-queue"
    )
    print("=" * 80)


if __name__ == "__main__":
    if not LANGSMITH_AVAILABLE:
        sys.exit(1)
    main()

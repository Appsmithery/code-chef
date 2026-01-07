"""
Automatic annotation of LangSmith traces for training dataset.

Usage:
    python support/scripts/evaluation/auto_annotate_traces.py --days 1
    python support/scripts/evaluation/auto_annotate_traces.py --experiment exp-2025-01-001
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    from langsmith import Client

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    print("❌ LangSmith not available. Install: pip install langsmith")

# Evaluation criteria
QUALITY_METRICS = {
    "intent_recognition": {
        "accuracy": lambda trace: verify_intent_matches_action(trace),
        "confidence_calibration": lambda trace: abs(
            trace.outputs.get("confidence", 0)
            - trace.metadata.get("actual_accuracy", 0)
        )
        < 0.2,
        "latency": lambda trace: (trace.end_time - trace.start_time).total_seconds()
        < 2.0,
        "token_efficiency": lambda trace: (
            trace.prompt_tokens < 500 if hasattr(trace, "prompt_tokens") else True
        ),
    },
    "orchestration": {
        "routing_accuracy": lambda trace: verify_agent_selection(trace),
        "subtask_quality": lambda trace: all(
            is_actionable(st) for st in trace.outputs.get("subtasks", [])
        ),
        "context_relevance": lambda trace: verify_context_used(trace),
        "completion_rate": lambda trace: trace.metadata.get("task_completed", False),
    },
}


def calculate_metrics(trace) -> Dict[str, float]:
    """Calculate quality metrics for a trace."""
    trace_type = trace.name

    # Normalize trace type
    if "intent" in trace_type.lower():
        trace_type = "intent_recognition"
    elif "workflow" in trace_type.lower() or "orchestrat" in trace_type.lower():
        trace_type = "orchestration"
    else:
        return {"overall_score": 0.5}

    if trace_type not in QUALITY_METRICS:
        return {"overall_score": 0.5}

    metrics = {}
    criteria = QUALITY_METRICS[trace_type]

    for metric_name, evaluator_fn in criteria.items():
        try:
            metrics[metric_name] = 1.0 if evaluator_fn(trace) else 0.0
        except Exception as e:
            metrics[metric_name] = 0.0

    metrics["overall_score"] = sum(metrics.values()) / len(metrics) if metrics else 0.5
    return metrics


def verify_intent_matches_action(trace) -> bool:
    """Verify predicted intent matches actual user action."""
    if not hasattr(trace, "outputs") or not trace.outputs:
        return False

    predicted_intent = trace.outputs.get("type")
    # Check subsequent traces to see if task was created
    actual_intent = (
        trace.metadata.get("actual_intent", predicted_intent)
        if hasattr(trace, "metadata")
        else predicted_intent
    )
    return predicted_intent == actual_intent


def verify_agent_selection(trace) -> bool:
    """Verify correct agent was selected for task."""
    if not hasattr(trace, "outputs") or not trace.outputs:
        return False

    selected_agent = trace.outputs.get("selected_agent")
    # Compare with task_type to validate routing
    task_type = trace.inputs.get("task_type") if hasattr(trace, "inputs") else None
    agent_map = {
        "feature-dev": "feature_dev",
        "code-review": "code_review",
        "infrastructure": "infrastructure",
        "cicd": "cicd",
        "documentation": "documentation",
    }
    expected_agent = agent_map.get(task_type)
    return selected_agent == expected_agent if expected_agent else True


def is_actionable(subtask: str) -> bool:
    """Check if subtask is clear and actionable."""
    if not subtask or not isinstance(subtask, str):
        return False
    return len(subtask) > 20 and any(
        verb in subtask.lower()
        for verb in [
            "implement",
            "create",
            "update",
            "fix",
            "add",
            "remove",
            "refactor",
        ]
    )


def verify_context_used(trace) -> bool:
    """Verify project context was utilized."""
    if not hasattr(trace, "inputs") or not trace.inputs:
        return False
    if not hasattr(trace, "metadata"):
        return False
    return bool(
        trace.inputs.get("project_context") or trace.metadata.get("workspace_name")
    )


async def annotate_recent_traces(days: int = 1, experiment_id: Optional[str] = None):
    """Annotate traces from last N days."""
    if not LANGSMITH_AVAILABLE:
        print("❌ LangSmith not available. Cannot annotate traces.")
        return

    client = Client()
    start_time = datetime.utcnow() - timedelta(days=days)

    filter_query = (
        f'start_time > "{start_time.isoformat()}" AND environment:"production"'
    )
    if experiment_id:
        filter_query += f' AND experiment_id:"{experiment_id}"'

    print(f"🔍 Fetching traces with filter: {filter_query}")

    # Fetch production traces
    try:
        traces = list(
            client.list_runs(project_name="code-chef-production", filter=filter_query)
        )
    except Exception as e:
        print(f"❌ Failed to fetch traces: {e}")
        return

    print(f"📊 Found {len(traces)} traces to annotate")

    annotated_count = 0
    for trace in traces:
        # Skip if already annotated
        if hasattr(trace, "feedback_stats") and any(
            f.key == "quality_score" for f in trace.feedback_stats
        ):
            continue

        # Calculate metrics
        metrics = calculate_metrics(trace)

        # Add annotation
        try:
            client.create_feedback(
                run_id=trace.id,
                key="quality_score",
                score=metrics["overall_score"],
                comment=f"Auto-evaluated: {metrics}",
                metadata={
                    "annotator": "auto",
                    "criteria": list(metrics.keys()),
                    "training_eligible": metrics["overall_score"] >= 0.8,
                },
            )

            annotated_count += 1

            # Export high-quality traces
            if metrics["overall_score"] >= 0.8:
                await export_for_training(trace, metrics)

        except Exception as e:
            print(f"⚠️  Failed to annotate trace {trace.id}: {e}")

    print(f"✅ Annotated {annotated_count} traces")


async def export_for_training(trace, metrics: Dict[str, float]):
    """Export trace to training dataset format."""
    output_dir = Path("support/data/training/annotated_traces")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract input from trace
    trace_input = ""
    if hasattr(trace, "inputs"):
        trace_input = (
            trace.inputs.get("prompt")
            or trace.inputs.get("message")
            or trace.inputs.get("task_description")
            or ""
        )

    training_example = {
        "trace_id": str(trace.id),
        "input": trace_input,
        "output": trace.outputs if hasattr(trace, "outputs") else {},
        "metadata": {
            "quality_score": metrics["overall_score"],
            "metrics": metrics,
            "timestamp": (
                trace.start_time.isoformat()
                if hasattr(trace, "start_time")
                else datetime.utcnow().isoformat()
            ),
            "agent": (
                trace.metadata.get("agent_name") if hasattr(trace, "metadata") else None
            ),
            "model": (
                trace.metadata.get("model_version")
                if hasattr(trace, "metadata")
                else None
            ),
        },
    }

    output_file = output_dir / f"{trace.id}.json"
    with open(output_file, "w") as f:
        json.dump(training_example, f, indent=2)


def auto_populate_annotation_queue():
    """Add uncertain traces to review queue automatically."""
    if not LANGSMITH_AVAILABLE:
        print("❌ LangSmith not available")
        return

    client = Client()

    # Query traces from last 24 hours with low confidence
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)

    print("🔍 Searching for uncertain traces...")

    try:
        traces = list(
            client.list_runs(
                project_name="code-chef-production",
                filter="lt(metadata.intent_confidence, 0.75)",
                start_time=start_time,
                end_time=end_time,
                limit=50,
            )
        )

        if not traces:
            print("ℹ️  No uncertain traces found in last 24 hours")
            return

        # Add to annotation queue
        queue_name = "uat-review-queue"
        added_count = 0

        for trace in traces:
            try:
                client.create_feedback(
                    run_id=trace.id,
                    key="needs_review",
                    score=1.0,
                    comment=f"Low confidence: {trace.extra.get('metadata', {}).get('intent_confidence', 'N/A')}",
                )
                added_count += 1
            except Exception as e:
                print(f"⚠️  Failed to flag trace {trace.id}: {e}")

        print(f"✅ Flagged {added_count} traces for review in {queue_name}")
        print(f"📊 View queue: https://smith.langchain.com/annotation-queues")

    except Exception as e:
        print(f"❌ Error querying traces: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-annotate LangSmith traces")
    parser.add_argument(
        "--days", type=int, default=1, help="Number of days to look back"
    )
    parser.add_argument(
        "--experiment", type=str, help="Specific experiment ID to annotate"
    )
    parser.add_argument(
        "--populate-queue",
        action="store_true",
        help="Populate annotation queue with uncertain traces",
    )

    args = parser.parse_args()

    if args.populate_queue:
        auto_populate_annotation_queue()
    else:
        asyncio.run(
            annotate_recent_traces(days=args.days, experiment_id=args.experiment)
        )

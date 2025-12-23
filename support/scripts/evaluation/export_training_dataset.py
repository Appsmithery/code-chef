"""
Export annotated LangSmith traces to HuggingFace dataset for training.

Output format:
- Dataset: alextorelli/code-chef-intent-recognition-v1
- Structure: {input: str, output: dict, metadata: dict}

Usage:
    python support/scripts/evaluation/export_training_dataset.py --min-quality 0.8 --max-samples 10000
"""

import asyncio
import os
from typing import Any, Dict, List

try:
    from datasets import Dataset, DatasetDict
    from langsmith import Client

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    print(
        "❌ Required dependencies not available. Install: pip install datasets langsmith huggingface-hub"
    )


async def export_training_dataset(min_quality: float = 0.8, max_samples: int = 10000):
    """Export high-quality traces to HuggingFace."""

    if not DEPENDENCIES_AVAILABLE:
        print("❌ Cannot export dataset. Install required dependencies.")
        return

    client = Client()

    # Fetch annotated traces
    print(f"🔍 Fetching annotated traces (quality >= {min_quality})")

    try:
        traces = list(
            client.list_runs(
                project_name="code-chef-production",
                filter=f"has:feedback.quality_score AND feedback.quality_score >= {min_quality}",
                limit=max_samples,
            )
        )
    except Exception as e:
        print(f"❌ Failed to fetch traces: {e}")
        return

    print(f"📊 Found {len(traces)} high-quality traces")

    # Convert to training format
    examples = []
    for trace in traces:
        try:
            feedback = (
                next(
                    (f for f in trace.feedback_stats if f.key == "quality_score"), None
                )
                if hasattr(trace, "feedback_stats")
                else None
            )
            if not feedback:
                continue

            # Extract input
            trace_input = ""
            if hasattr(trace, "inputs") and trace.inputs:
                trace_input = (
                    trace.inputs.get("prompt")
                    or trace.inputs.get("message")
                    or trace.inputs.get("task_description")
                    or ""
                )

            if not trace_input:
                continue  # Skip traces without input

            example = {
                "input": trace_input,
                "output": trace.outputs if hasattr(trace, "outputs") else {},
                "metadata": {
                    "trace_id": str(trace.id),
                    "quality_score": (
                        feedback.score if hasattr(feedback, "score") else 0.8
                    ),
                    "timestamp": (
                        trace.start_time.isoformat()
                        if hasattr(trace, "start_time")
                        else ""
                    ),
                    "agent": (
                        trace.metadata.get("agent_name")
                        if hasattr(trace, "metadata")
                        else None
                    ),
                    "model": (
                        trace.metadata.get("model_version")
                        if hasattr(trace, "metadata")
                        else None
                    ),
                    "latency_ms": (
                        (trace.end_time - trace.start_time).total_seconds() * 1000
                        if hasattr(trace, "end_time") and hasattr(trace, "start_time")
                        else 0
                    ),
                    "tokens": (
                        (trace.prompt_tokens + trace.completion_tokens)
                        if hasattr(trace, "prompt_tokens")
                        and hasattr(trace, "completion_tokens")
                        else 0
                    ),
                },
            }
            examples.append(example)
        except Exception as e:
            print(f"⚠️  Failed to process trace {trace.id}: {e}")
            continue

    if len(examples) == 0:
        print("❌ No annotated traces found. Run auto_annotate_traces.py first.")
        return

    print(f"✅ Processed {len(examples)} examples")

    # Split into train/validation/test (80/10/10)
    dataset = Dataset.from_list(examples)
    dataset_dict = dataset.train_test_split(test_size=0.2, seed=42)
    val_test = dataset_dict["test"].train_test_split(test_size=0.5, seed=42)

    final_dataset = DatasetDict(
        {
            "train": dataset_dict["train"],
            "validation": val_test["train"],
            "test": val_test["test"],
        }
    )

    print(f"\n📊 Dataset splits:")
    print(f"   Train: {len(final_dataset['train'])} examples")
    print(f"   Validation: {len(final_dataset['validation'])} examples")
    print(f"   Test: {len(final_dataset['test'])} examples")

    # Check if HuggingFace token is available
    hf_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
    if not hf_token:
        print(
            "\n⚠️  HUGGINGFACE_TOKEN not set. Dataset will not be uploaded to HuggingFace."
        )
        print("   Set token: export HUGGINGFACE_TOKEN=hf_...")

        # Save locally instead
        local_path = "support/data/training/dataset"
        final_dataset.save_to_disk(local_path)
        print(f"\n💾 Dataset saved locally to: {local_path}")
        return

    # Upload to HuggingFace
    try:
        final_dataset.push_to_hub(
            "alextorelli/code-chef-intent-recognition-v1", private=False, token=hf_token
        )

        print(f"\n✅ Dataset uploaded to HuggingFace")
        print(
            f"📊 Dataset URL: https://huggingface.co/datasets/alextorelli/code-chef-intent-recognition-v1"
        )
    except Exception as e:
        print(f"\n❌ Failed to upload dataset: {e}")

        # Save locally as fallback
        local_path = "support/data/training/dataset"
        final_dataset.save_to_disk(local_path)
        print(f"\n💾 Dataset saved locally to: {local_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Export training dataset to HuggingFace"
    )
    parser.add_argument(
        "--min-quality", type=float, default=0.8, help="Minimum quality score"
    )
    parser.add_argument(
        "--max-samples", type=int, default=10000, help="Maximum samples to export"
    )

    args = parser.parse_args()

    asyncio.run(
        export_training_dataset(
            min_quality=args.min_quality, max_samples=args.max_samples
        )
    )

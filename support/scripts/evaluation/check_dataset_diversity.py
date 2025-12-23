"""
Check training dataset diversity and identify underrepresented intents.

Usage:
    python support/scripts/evaluation/check_dataset_diversity.py
"""

import os
from collections import Counter

try:
    from datasets import load_dataset
    from langsmith import Client

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    print(
        "❌ Required dependencies not available. Install: pip install datasets langsmith"
    )


def check_diversity():
    """Check dataset diversity and flag underrepresented classes."""

    if not DEPENDENCIES_AVAILABLE:
        print("❌ Cannot check diversity. Install required dependencies.")
        return

    client = Client()

    # Load current training dataset
    try:
        dataset = load_dataset(
            "alextorelli/code-chef-intent-recognition-v1", split="train"
        )
    except Exception as e:
        print(f"❌ Dataset not found: {e}")
        print("   Export traces first using export_training_dataset.py")
        return

    # Count intent distribution
    intent_counts = Counter()
    for ex in dataset:
        intent_type = None
        if isinstance(ex.get("output"), dict):
            intent_type = ex["output"].get("type")
        elif isinstance(ex.get("output"), str):
            # Try to parse if it's a JSON string
            try:
                import json

                output_dict = json.loads(ex["output"])
                intent_type = output_dict.get("type")
            except:
                pass

        if intent_type:
            intent_counts[intent_type] += 1

    print("\n📊 Intent Distribution:")
    for intent, count in intent_counts.most_common():
        percentage = (count / len(dataset)) * 100
        print(f"   {intent:25s}: {count:4d} examples ({percentage:5.1f}%)")

    # Identify underrepresented intents (< 50 examples)
    rare_intents = [intent for intent, count in intent_counts.items() if count < 50]

    if rare_intents:
        print(f"\n⚠️  Underrepresented Intents (< 50 examples):")
        for intent in rare_intents:
            print(f"   - {intent}: {intent_counts[intent]} examples")

        # Flag traces with rare intents for priority annotation
        print(f"\n🔍 Searching for traces with rare intents...")

        try:
            for intent in rare_intents:
                traces = list(
                    client.list_runs(
                        project_name="code-chef-production",
                        filter=f'outputs.type:"{intent}"',
                        limit=100,
                    )
                )

                flagged = 0
                for trace in traces:
                    try:
                        client.create_feedback(
                            run_id=trace.id,
                            key="diversity_sampling",
                            value=True,
                            comment=f"Rare intent '{intent}' - prioritize for training",
                            metadata={
                                "review_priority": "high",
                                "add_to_training": True,
                                "intent_type": intent,
                            },
                        )
                        flagged += 1
                    except Exception as e:
                        # May already be flagged
                        pass

                if flagged > 0:
                    print(f"   ✅ Flagged {flagged} traces for intent '{intent}'")
        except Exception as e:
            print(f"\n⚠️  Failed to flag traces: {e}")
    else:
        print("\n✅ All intents well-represented (≥ 50 examples each)")

    # Calculate diversity metrics
    total = sum(intent_counts.values())
    num_intents = len(intent_counts)

    if num_intents > 0:
        # Shannon entropy (diversity metric)
        import math

        entropy = -sum(
            (count / total) * math.log2(count / total)
            for count in intent_counts.values()
        )
        max_entropy = math.log2(num_intents)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

        print(f"\n📈 Diversity Metrics:")
        print(f"   Total examples: {total}")
        print(f"   Unique intents: {num_intents}")
        print(f"   Shannon entropy: {entropy:.3f}")
        print(f"   Normalized diversity: {normalized_entropy:.1%}")

        if normalized_entropy < 0.7:
            print(
                f"\n⚠️  Dataset diversity is LOW (< 70%). Consider collecting more examples for underrepresented intents."
            )
        else:
            print(f"\n✅ Dataset diversity is GOOD (≥ 70%)")


if __name__ == "__main__":
    check_diversity()

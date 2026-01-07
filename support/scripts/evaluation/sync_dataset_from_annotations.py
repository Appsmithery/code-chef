"""
Sync annotated traces from production to evaluation dataset.

This script automates dataset building by:
1. Querying LangSmith for recently annotated traces
2. Filtering based on feedback scores and tags
3. Adding high-quality examples to evaluation dataset
4. Removing low-quality or outdated examples

Usage:
    # Sync last 7 days of annotations
    python support/scripts/evaluation/sync_dataset_from_annotations.py \
        --dataset code-chef-gold-standard-v1 \
        --days 7

    # Dry run to preview changes
    python support/scripts/evaluation/sync_dataset_from_annotations.py \
        --dataset code-chef-gold-standard-v1 \
        --dry-run

    # Sync specific failure categories
    python support/scripts/evaluation/sync_dataset_from_annotations.py \
        --dataset code-chef-gold-standard-v1 \
        --categories agent_routing,token_efficiency

Linear Issue: DEV-195
Documentation: support/docs/operations/LLM_OPERATIONS.md
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# LangSmith imports
try:
    from langsmith import Client

    LANGSMITH_AVAILABLE = True
except ImportError:
    logger.error("LangSmith not available. Install with: pip install langsmith")
    LANGSMITH_AVAILABLE = False
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_DATASET = "code-chef-gold-standard-v1"
DEFAULT_PROJECT = "code-chef-production"

# Quality thresholds for dataset inclusion
MIN_CORRECTNESS_SCORE = 0.7  # Only include high-quality examples
MIN_FEEDBACK_COUNT = 1  # At least one feedback rating

# Categories to include (based on evaluator types)
VALID_CATEGORIES = [
    "agent_routing",
    "token_efficiency",
    "latency",
    "workflow_completeness",
    "mcp_integration",
    "risk_assessment",
    "modelops",
    "streaming",
]


# =============================================================================
# DATASET SYNC
# =============================================================================


class DatasetSyncer:
    """Syncs annotated traces to evaluation dataset."""

    def __init__(self, client: Client, dataset_name: str, project_name: str):
        """
        Initialize dataset syncer.

        Args:
            client: LangSmith client
            dataset_name: Target dataset name
            project_name: Source project name
        """
        self.client = client
        self.dataset_name = dataset_name
        self.project_name = project_name
        self.dataset = None

    def _ensure_dataset_exists(self) -> None:
        """Ensure target dataset exists, create if needed."""
        try:
            self.dataset = self.client.read_dataset(dataset_name=self.dataset_name)
            logger.info(f"Using existing dataset: {self.dataset_name}")
        except Exception:
            logger.info(f"Creating new dataset: {self.dataset_name}")
            self.dataset = self.client.create_dataset(
                dataset_name=self.dataset_name,
                description="Gold standard evaluation dataset for code-chef",
            )

    def query_annotated_traces(
        self,
        days: int = 7,
        categories: Optional[List[str]] = None,
    ) -> List[Any]:
        """
        Query annotated traces from production.

        Args:
            days: Number of days to look back
            categories: Optional list of failure categories to filter

        Returns:
            List of annotated runs
        """
        start_time = datetime.now() - timedelta(days=days)

        # Build filter
        filter_parts = [
            "has(feedback)",  # Must have feedback
            f'feedback_scores["correctness"] >= {MIN_CORRECTNESS_SCORE}',
        ]

        # Add category filter if specified
        if categories:
            category_filter = " or ".join([f'"{cat}" in tags' for cat in categories])
            filter_parts.append(f"({category_filter})")

        filter_str = " and ".join(filter_parts)

        logger.info(f"Querying traces with filter: {filter_str}")

        # Query runs
        runs = list(
            self.client.list_runs(
                project_name=self.project_name,
                filter=filter_str,
                start_time=start_time,
                run_type="chain",  # Only chain runs (full workflows)
            )
        )

        logger.info(f"Found {len(runs)} annotated traces")
        return runs

    def convert_run_to_example(self, run: Any) -> Optional[Dict[str, Any]]:
        """
        Convert annotated run to evaluation example.

        Args:
            run: LangSmith run object

        Returns:
            Example dict or None if invalid
        """
        try:
            # Extract inputs
            inputs = run.inputs or {}
            query = inputs.get("message") or inputs.get("query")

            if not query:
                logger.warning(f"Run {run.id} missing query input")
                return None

            # Extract expected output from reference example or annotation
            outputs = {}

            # Get feedback scores
            feedback_scores = {}
            if hasattr(run, "feedback_stats") and run.feedback_stats:
                for feedback in run.feedback_stats:
                    feedback_scores[feedback.key] = feedback.score

            # Get failure category from tags
            category = None
            if hasattr(run, "tags") and run.tags:
                for tag in run.tags:
                    if tag in VALID_CATEGORIES:
                        category = tag
                        break

            # Build example
            example = {
                "inputs": {"query": query},
                "outputs": {
                    "expected_agent": run.outputs.get("agent") if run.outputs else None,
                    "expected_tokens": (
                        run.outputs.get("tokens") if run.outputs else None
                    ),
                },
                "metadata": {
                    "source": "production_annotation",
                    "run_id": str(run.id),
                    "correctness": feedback_scores.get("correctness"),
                    "category": category,
                    "created_at": (
                        run.start_time.isoformat() if run.start_time else None
                    ),
                },
            }

            return example

        except Exception as e:
            logger.error(f"Failed to convert run {run.id}: {e}")
            return None

    def add_examples_to_dataset(
        self, examples: List[Dict[str, Any]], dry_run: bool = False
    ) -> int:
        """
        Add examples to dataset, avoiding duplicates.

        Args:
            examples: List of example dicts
            dry_run: If True, only preview changes

        Returns:
            Number of examples added
        """
        if not examples:
            logger.info("No examples to add")
            return 0

        # Get existing examples to check for duplicates
        existing_examples = list(self.client.list_examples(dataset_id=self.dataset.id))
        existing_queries = {
            ex.inputs.get("query") for ex in existing_examples if ex.inputs
        }

        # Filter out duplicates
        new_examples = [
            ex for ex in examples if ex["inputs"]["query"] not in existing_queries
        ]

        if not new_examples:
            logger.info("All examples already in dataset (duplicates)")
            return 0

        logger.info(f"Adding {len(new_examples)} new examples to dataset")

        if dry_run:
            logger.info("DRY RUN - would add:")
            for ex in new_examples[:5]:  # Show first 5
                logger.info(f"  - {ex['inputs']['query'][:80]}...")
            if len(new_examples) > 5:
                logger.info(f"  - ... and {len(new_examples) - 5} more")
            return len(new_examples)

        # Add examples
        added = 0
        for example in new_examples:
            try:
                self.client.create_example(
                    inputs=example["inputs"],
                    outputs=example["outputs"],
                    dataset_id=self.dataset.id,
                    metadata=example["metadata"],
                )
                added += 1
            except Exception as e:
                logger.error(f"Failed to add example: {e}")

        logger.info(f"Successfully added {added} examples")
        return added

    def remove_outdated_examples(self, days: int = 90, dry_run: bool = False) -> int:
        """
        Remove examples older than specified days.

        Args:
            days: Keep examples newer than this
            dry_run: If True, only preview changes

        Returns:
            Number of examples removed
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        existing_examples = list(self.client.list_examples(dataset_id=self.dataset.id))

        outdated = []
        for example in existing_examples:
            metadata = example.metadata or {}
            created_at_str = metadata.get("created_at")

            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    if created_at < cutoff_date:
                        outdated.append(example)
                except Exception:
                    pass

        if not outdated:
            logger.info("No outdated examples to remove")
            return 0

        logger.info(
            f"Removing {len(outdated)} outdated examples (older than {days} days)"
        )

        if dry_run:
            logger.info("DRY RUN - would remove:")
            for ex in outdated[:5]:  # Show first 5
                query = ex.inputs.get("query", "N/A")[:80] if ex.inputs else "N/A"
                logger.info(f"  - {query}...")
            if len(outdated) > 5:
                logger.info(f"  - ... and {len(outdated) - 5} more")
            return len(outdated)

        # Remove examples
        removed = 0
        for example in outdated:
            try:
                self.client.delete_example(example_id=example.id)
                removed += 1
            except Exception as e:
                logger.error(f"Failed to remove example {example.id}: {e}")

        logger.info(f"Successfully removed {removed} examples")
        return removed

    def sync(
        self,
        days: int = 7,
        categories: Optional[List[str]] = None,
        remove_outdated: bool = True,
        outdated_days: int = 90,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        Sync annotations to dataset.

        Args:
            days: Number of days to look back for annotations
            categories: Optional list of categories to filter
            remove_outdated: Whether to remove old examples
            outdated_days: Age threshold for removal
            dry_run: If True, only preview changes

        Returns:
            Summary of changes made
        """
        logger.info(f"Starting dataset sync: {self.dataset_name}")

        # Ensure dataset exists
        self._ensure_dataset_exists()

        # Query annotated traces
        runs = self.query_annotated_traces(days=days, categories=categories)

        # Convert to examples
        examples = []
        for run in runs:
            example = self.convert_run_to_example(run)
            if example:
                examples.append(example)

        logger.info(f"Converted {len(examples)} runs to examples")

        # Add new examples
        added = self.add_examples_to_dataset(examples, dry_run=dry_run)

        # Remove outdated examples
        removed = 0
        if remove_outdated:
            removed = self.remove_outdated_examples(days=outdated_days, dry_run=dry_run)

        # Summary
        summary = {
            "traces_queried": len(runs),
            "examples_converted": len(examples),
            "examples_added": added,
            "examples_removed": removed,
        }

        logger.info("Sync complete:")
        logger.info(f"  Traces queried: {summary['traces_queried']}")
        logger.info(f"  Examples converted: {summary['examples_converted']}")
        logger.info(f"  Examples added: {summary['examples_added']}")
        logger.info(f"  Examples removed: {summary['examples_removed']}")

        return summary


# =============================================================================
# ANNOTATION QUEUE SYNC
# =============================================================================


def sync_reviewed_traces_from_queue(
    queue_name: str = "uat-review-queue", dataset_name: str = DEFAULT_DATASET
):
    """
    Move reviewed traces from annotation queue to gold standard dataset.

    Args:
        queue_name: Name of the annotation queue
        dataset_name: Target dataset name
    """
    if not LANGSMITH_AVAILABLE:
        logger.error("LangSmith not available")
        return

    client = Client()

    logger.info(f"Syncing from queue '{queue_name}' to dataset '{dataset_name}'")

    try:
        # Get runs with feedback marked as reviewed
        runs = list(
            client.list_runs(
                project_name=DEFAULT_PROJECT,
                filter='eq(feedback_key, "needs_review") and eq(feedback_score, 0.0)',  # Score 0 = reviewed
                limit=100,
            )
        )

        if not runs:
            logger.info("No reviewed traces found in queue")
            return

        # Ensure dataset exists
        try:
            dataset = client.read_dataset(dataset_name=dataset_name)
        except Exception:
            logger.info(f"Creating dataset: {dataset_name}")
            dataset = client.create_dataset(
                dataset_name=dataset_name,
                description="Gold standard evaluation dataset from UAT reviews",
            )

        # Add reviewed runs to dataset
        added_count = 0
        for run in runs:
            try:
                # Get human annotation from feedback
                feedbacks = list(client.list_feedback(run_ids=[run.id]))

                # Extract score and comment
                human_score = None
                reviewer_notes = ""
                for feedback in feedbacks:
                    if feedback.key == "human_quality_score":
                        human_score = feedback.score
                    if feedback.key == "reviewer_notes":
                        reviewer_notes = feedback.comment or ""

                # Create dataset example with reference output
                client.create_example(
                    dataset_id=dataset.id,
                    inputs=run.inputs,
                    outputs=run.outputs,
                    metadata={
                        "human_score": human_score,
                        "reviewer_notes": reviewer_notes,
                        "original_run_id": str(run.id),
                        "review_date": datetime.utcnow().isoformat(),
                        "source": "annotation_queue",
                        "module": run.extra.get("metadata", {}).get(
                            "module", "unknown"
                        ),
                    },
                )

                added_count += 1
                logger.info(f"Added run {run.id} to dataset")

            except Exception as e:
                logger.warning(f"Failed to add run {run.id}: {e}")

        logger.success(f"✅ Synced {added_count} examples from queue to {dataset_name}")

    except Exception as e:
        logger.error(f"Error syncing from queue: {e}")


# =============================================================================
# CLI
# =============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync annotated traces to evaluation dataset"
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Target dataset name (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help=f"Source project name (default: {DEFAULT_PROJECT})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "--categories",
        help="Comma-separated list of categories to filter (optional)",
    )
    parser.add_argument(
        "--no-remove-outdated",
        action="store_true",
        help="Don't remove outdated examples",
    )
    parser.add_argument(
        "--outdated-days",
        type=int,
        default=90,
        help="Age threshold for removal (default: 90 days)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    parser.add_argument(
        "--from-queue",
        action="store_true",
        help="Sync from annotation queue instead of general traces",
    )
    parser.add_argument(
        "--queue-name",
        default="uat-review-queue",
        help="Annotation queue name (default: uat-review-queue)",
    )

    args = parser.parse_args()

    # If syncing from queue, use dedicated function
    if args.from_queue:
        sync_reviewed_traces_from_queue(
            queue_name=args.queue_name, dataset_name=args.dataset
        )
        return

    # Parse categories
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
        # Validate categories
        invalid = [c for c in categories if c not in VALID_CATEGORIES]
        if invalid:
            logger.error(f"Invalid categories: {invalid}")
            logger.error(f"Valid categories: {VALID_CATEGORIES}")
            sys.exit(1)

    # Create client
    client = Client()

    # Create syncer
    syncer = DatasetSyncer(
        client=client,
        dataset_name=args.dataset,
        project_name=args.project,
    )

    # Run sync
    summary = syncer.sync(
        days=args.days,
        categories=categories,
        remove_outdated=not args.no_remove_outdated,
        outdated_days=args.outdated_days,
        dry_run=args.dry_run,
    )

    # Output summary
    print("\n" + "=" * 80)
    print("SYNC SUMMARY")
    print("=" * 80)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Test script for ModelOps training integration.

Prerequisites:
1. HuggingFace Space deployed (see MANUAL_DEPLOY.md)
2. Environment variables set:
   - HUGGINGFACE_TOKEN: HF API token
   - MODELOPS_SPACE_URL: Space URL (optional, uses default)
3. LangSmith API key configured

Usage:
    # Test health check only
    python test_modelops_integration.py --health-only

    # Run demo training job
    python test_modelops_integration.py --demo

    # Full integration test (requires LangSmith data)
    python test_modelops_integration.py --full
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from loguru import logger

from agent_orchestrator.agents.infrastructure.modelops.training import (
    ModelOpsTrainer,
    ModelOpsTrainerClient,
)

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_health_check():
    """Test Space health endpoint."""
    logger.info("Testing ModelOps Space health check...")

    client = ModelOpsTrainerClient()
    health = client.health_check()

    if health.get("status") == "healthy":
        logger.success(f"✓ Space is healthy: {health}")
        return True
    else:
        logger.error(f"✗ Space health check failed: {health}")
        return False


def test_demo_training():
    """Test demo training job with synthetic data."""
    logger.info("Testing demo training job...")

    client = ModelOpsTrainerClient()

    # Create synthetic CSV data
    synthetic_data = """text,response
"def hello():","\tprint('Hello, world!')"
"def add(a, b):","\treturn a + b"
"class Person:","\tdef __init__(self, name):\n\t\tself.name = name"
"import os","# Standard library import"
"from typing import List","# Type hints import"
"""

    # Submit demo job
    try:
        job = client.submit_training_job(
            csv_data=synthetic_data,
            base_model="microsoft/Phi-3-mini-4k-instruct",
            project_name="test-demo-training",
            is_demo=True,
        )

        logger.success(f"✓ Demo job submitted: {job['job_id']}")
        logger.info(f"  Cost estimate: ${job.get('estimated_cost', 'unknown')}")
        logger.info(f"  Duration: {job.get('expected_duration', 'unknown')}")

        # Monitor for 2 minutes max (demo should complete quickly)
        logger.info("Monitoring job (max 2 minutes)...")
        final_status = client.wait_for_completion(
            job_id=job["job_id"], poll_interval=15, max_wait=120
        )

        if final_status["status"] == "completed":
            logger.success(f"✓ Demo training completed: {final_status['model_id']}")
            return True
        else:
            logger.error(
                f"✗ Demo training failed: {final_status.get('error', 'Unknown')}"
            )
            return False

    except Exception as e:
        logger.error(f"✗ Demo training error: {e}")
        return False


def test_full_integration():
    """Test full integration with LangSmith data export."""
    logger.info("Testing full ModelOps integration...")

    trainer = ModelOpsTrainer()

    # Test LangSmith export (requires active LangSmith project)
    try:
        logger.info("Exporting data from LangSmith...")
        df = trainer.export_langsmith_data(
            project_name="code-chef-infrastructure",  # Use actual project
            limit=20,  # Small sample
        )

        logger.success(f"✓ Exported {len(df)} examples from LangSmith")

        if len(df) < 10:
            logger.warning("Not enough data for training (need 10+ examples)")
            return False

        # Submit demo training job with real data
        logger.info("Submitting training job with LangSmith data...")
        job = trainer.train_model(
            agent_name="infrastructure",
            langsmith_project="code-chef-infrastructure",
            base_model_preset="phi-3-mini",
            is_demo=True,
            export_limit=20,
        )

        logger.success(f"✓ Training job submitted: {job['job_id']}")
        logger.info(f"  Training examples: {job['training_examples']}")
        logger.info(f"  Base model: {job['base_model']}")
        logger.info(f"  Hardware: {job['hardware']}")

        # Monitor job
        logger.info("Monitoring training job...")
        final_status = trainer.monitor_training(job["job_id"])

        if final_status["status"] == "completed":
            logger.success(f"✓ Full integration test passed!")
            logger.success(f"  Model: {final_status['model_id']}")
            return True
        else:
            logger.error(f"✗ Training failed: {final_status.get('error', 'Unknown')}")
            return False

    except Exception as e:
        logger.error(f"✗ Full integration test error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run ModelOps integration tests."""
    parser = argparse.ArgumentParser(description="Test ModelOps training integration")
    parser.add_argument(
        "--health-only", action="store_true", help="Only test health check"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Run demo training job with synthetic data"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full integration test with LangSmith data",
    )

    args = parser.parse_args()

    # Check environment
    if not os.getenv("HUGGINGFACE_TOKEN"):
        logger.error("HUGGINGFACE_TOKEN environment variable not set")
        sys.exit(1)

    results = []

    # Always run health check
    logger.info("=" * 60)
    logger.info("ModelOps Integration Tests")
    logger.info("=" * 60)

    health_ok = test_health_check()
    results.append(("Health Check", health_ok))

    if not health_ok:
        logger.error("Health check failed - Space may not be deployed yet")
        logger.info("See deploy/huggingface-spaces/modelops-trainer/MANUAL_DEPLOY.md")
        sys.exit(1)

    if args.health_only:
        logger.info("\n✓ Health check passed!")
        sys.exit(0)

    # Run demo training if requested
    if args.demo or not args.full:
        logger.info("\n" + "=" * 60)
        demo_ok = test_demo_training()
        results.append(("Demo Training", demo_ok))

    # Run full integration if requested
    if args.full:
        logger.info("\n" + "=" * 60)
        full_ok = test_full_integration()
        results.append(("Full Integration", full_ok))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

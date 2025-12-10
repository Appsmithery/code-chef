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

from agent_orchestrator.agents.infrastructure.modelops.coordinator import (
    ModelOpsCoordinator,
)
from agent_orchestrator.agents.infrastructure.modelops.deployment import (
    ModelOpsDeployment,
)
from agent_orchestrator.agents.infrastructure.modelops.evaluation import ModelEvaluator
from agent_orchestrator.agents.infrastructure.modelops.registry import ModelRegistry
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


async def test_end_to_end_workflow():
    """Test complete workflow: train → evaluate → deploy → rollback."""
    logger.info("Testing end-to-end ModelOps workflow...")

    # Use temporary registry for testing
    import tempfile

    temp_dir = tempfile.mkdtemp()
    registry_path = os.path.join(temp_dir, "test_registry.json")

    try:
        # Initialize components
        registry = ModelRegistry(registry_path=registry_path)
        coordinator = ModelOpsCoordinator(registry=registry)

        # Step 1: Train a model (demo mode)
        logger.info("\n[1/4] Training model...")
        train_result = await coordinator.route_request(
            "Train feature_dev model",
            {
                "agent_name": "feature_dev",
                "langsmith_project": "code-chef-feature-dev",
                "base_model_preset": "phi-3-mini",
                "is_demo": True,
            },
        )

        if "error" in train_result:
            logger.error(f"✗ Training failed: {train_result['error']}")
            return False

        logger.success(f"✓ Training job submitted: {train_result['job_id']}")

        # Wait for training to complete (demo should be fast)
        trainer = ModelOpsTrainer(registry=registry)
        final_status = await trainer.monitor_training(train_result["job_id"])

        if final_status["status"] != "completed":
            logger.error(f"✗ Training did not complete: {final_status}")
            return False

        model_repo = final_status["model_id"]
        logger.success(f"✓ Training completed: {model_repo}")

        # Step 2: Evaluate model (mock for now - would use real evaluation)
        logger.info("\n[2/4] Evaluating model...")

        # For integration test, we'll simulate evaluation by directly adding to registry
        from agent_orchestrator.agents.infrastructure.modelops.registry import (
            EvaluationScores,
            ModelVersion,
            TrainingConfig,
        )

        training_config = TrainingConfig(
            base_model="microsoft/Phi-3-mini-4k-instruct",
            training_method="sft",
            training_dataset="ls://feature-dev-train",
            eval_dataset="ls://feature-dev-eval",
        )

        eval_scores = EvaluationScores(
            accuracy=0.87,
            baseline_improvement_pct=15.2,
            avg_latency_ms=1200.0,
            cost_per_1k_tokens=0.003,
        )

        version = ModelVersion(
            version="v1.0.0",
            model_id=model_repo,
            training_config=training_config,
            trained_at=final_status.get("completed_at"),
            trained_by="integration-test",
            job_id=train_result["job_id"],
            hub_repo=model_repo,
            eval_scores=eval_scores,
            deployment_status="not_deployed",
        )

        registry.add_version("feature_dev", version)
        logger.success(f"✓ Evaluation complete (simulated): 15.2% improvement")

        # Step 3: Deploy to production
        logger.info("\n[3/4] Deploying to production...")

        # Create temp models.yaml for testing
        models_yaml_path = os.path.join(temp_dir, "models.yaml")
        import yaml

        with open(models_yaml_path, "w") as f:
            yaml.safe_dump(
                {
                    "version": "1.1",
                    "provider": "openrouter",
                    "openrouter": {
                        "base_url": "https://openrouter.ai/api/v1",
                        "agent_models": {
                            "feature_dev": "qwen/qwen-2.5-coder-32b-instruct"
                        },
                    },
                },
                f,
            )

        deployment = ModelOpsDeployment(
            registry=registry, models_config_path=models_yaml_path
        )

        deploy_result = await deployment.deploy_model_to_agent(
            agent_name="feature_dev",
            model_repo=model_repo,
            version="v1.0.0",
        )

        logger.success(f"✓ Deployed to production")

        # Step 4: Rollback
        logger.info("\n[4/4] Testing rollback...")

        # Add previous version to registry
        old_version = ModelVersion(
            version="v0.9.0",
            model_id="qwen/qwen-2.5-coder-32b-instruct",
            training_config=training_config,
            trained_at="2025-12-09T10:00:00Z",
            trained_by="integration-test",
            job_id="old-job-123",
            hub_repo="qwen/qwen-2.5-coder-32b-instruct",
            deployment_status="deployed",
            deployed_at="2025-12-09T10:30:00Z",
        )

        registry.add_version("feature_dev", old_version)

        rollback_result = await deployment.rollback_deployment(agent_name="feature_dev")

        logger.success(f"✓ Rolled back to: {rollback_result.version}")

        # Verify rollback
        current = await deployment.get_current_model("feature_dev")
        if current["version"] == "v0.9.0":
            logger.success("✓ End-to-end workflow test passed!")
            return True
        else:
            logger.error(f"✗ Rollback verification failed: {current}")
            return False

    except Exception as e:
        logger.error(f"✗ Workflow test error: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


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
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="Run end-to-end workflow test (train → evaluate → deploy → rollback)",
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

    # Run end-to-end workflow if requested
    if args.workflow:
        logger.info("\n" + "=" * 60)
        import asyncio

        workflow_ok = asyncio.run(test_end_to_end_workflow())
        results.append(("End-to-End Workflow", workflow_ok))

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

"""ModelOps coordinator for routing and orchestrating model operations.

Central orchestration for training, evaluation, and deployment operations.
Routes ModelOps requests to appropriate handlers.
"""

from typing import Any, Dict, Optional

from langsmith import traceable

from .deployment import ModelOpsDeployment
from .evaluation import ModelEvaluator
from .registry import ModelRegistry
from .training import ModelOpsTrainer


class ModelOpsCoordinator:
    """Coordinates ModelOps operations across training, evaluation, and deployment."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        trainer: Optional[ModelOpsTrainer] = None,
        evaluator: Optional[ModelEvaluator] = None,
        deployment: Optional[ModelOpsDeployment] = None,
    ):
        """Initialize ModelOps coordinator.

        Args:
            registry: ModelRegistry instance (creates new if None)
            trainer: ModelOpsTrainer instance (creates new if None)
            evaluator: ModelEvaluator instance (creates new if None)
            deployment: ModelOpsDeployment instance (creates new if None)
        """
        self.registry = registry or ModelRegistry()
        self.trainer = trainer or ModelOpsTrainer(registry=self.registry)
        self.evaluator = evaluator or ModelEvaluator(registry=self.registry)
        self.deployment = deployment or ModelOpsDeployment(registry=self.registry)

    @traceable(name="modelops_route")
    async def route_request(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route ModelOps request to appropriate handler.

        Args:
            message: User message/intent
            context: Additional context (agent_name, model_id, etc.)

        Returns:
            Result dictionary from handler
        """
        message_lower = message.lower()

        # Training operations
        if "train" in message_lower and "model" in message_lower:
            return await self._handle_training(context)

        # Evaluation operations
        elif "evaluate" in message_lower and "model" in message_lower:
            return await self._handle_evaluation(context)

        # Deployment operations
        elif "deploy" in message_lower and "model" in message_lower:
            return await self._handle_deployment(context)

        # Canary promotion
        elif "promote" in message_lower and "canary" in message_lower:
            return await self._handle_canary_promotion(context)

        # Rollback operations
        elif "rollback" in message_lower:
            return await self._handle_rollback(context)

        # List operations
        elif "list" in message_lower and "model" in message_lower:
            return await self._handle_list_models(context)

        # Monitor operations
        elif "monitor" in message_lower and (
            "job" in message_lower or "training" in message_lower
        ):
            return await self._handle_monitor_training(context)

        # Status/current model
        elif "current" in message_lower or "status" in message_lower:
            return await self._handle_status(context)

        else:
            return {
                "error": "Unknown ModelOps intent",
                "message": message,
                "supported_operations": [
                    "train model",
                    "evaluate model",
                    "deploy model",
                    "promote canary",
                    "rollback deployment",
                    "list models",
                    "monitor training",
                    "check status",
                ],
            }

    @traceable(name="modelops_train")
    async def _handle_training(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model training request.

        Expected context:
            agent_name: Agent to train for
            langsmith_project: LangSmith project with training data
            base_model_preset: Model preset (phi-3-mini, codellama-7b, etc.)
            is_demo: Whether to run demo mode
        """
        agent_name = context.get("agent_name")
        langsmith_project = context.get("langsmith_project")
        base_model_preset = context.get("base_model_preset", "phi-3-mini")
        is_demo = context.get("is_demo", False)

        if not agent_name:
            return {"error": "agent_name required", "context": context}

        if not langsmith_project:
            # Auto-detect from agent name
            langsmith_project = f"code-chef-{agent_name}"

        # Submit training job
        result = await self.trainer.train_model(
            agent_name=agent_name,
            langsmith_project=langsmith_project,
            base_model_preset=base_model_preset,
            is_demo=is_demo,
        )

        return {
            "operation": "train",
            "agent_name": agent_name,
            "job_id": result.get("job_id"),
            "status": result.get("status"),
            "estimated_duration": result.get("estimated_duration_minutes"),
            "estimated_cost": result.get("estimated_cost"),
            "trackio_url": result.get("trackio_url"),
            "message": f"Training job submitted for {agent_name}. Monitor at {result.get('trackio_url')}",
        }

    @traceable(name="modelops_evaluate")
    async def _handle_evaluation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model evaluation request.

        Expected context:
            agent_name: Agent to evaluate
            candidate_model: Candidate model to test
            eval_dataset_name: LangSmith eval dataset name
        """
        agent_name = context.get("agent_name")
        candidate_model = context.get("candidate_model")
        eval_dataset_name = context.get("eval_dataset_name")

        if not agent_name:
            return {"error": "agent_name required", "context": context}

        if not candidate_model:
            return {"error": "candidate_model required", "context": context}

        # Get current baseline model
        agent_data = self.registry.get_agent(agent_name)
        if not agent_data or not agent_data.current:
            return {
                "error": f"No baseline model found for {agent_name}",
                "suggestion": "Train a model first or specify baseline_model in context",
            }

        baseline_model = agent_data.current.model_id

        # Run comparison
        comparison = await self.evaluator.compare_models(
            agent_name=agent_name,
            baseline_model=baseline_model,
            candidate_model=candidate_model,
            eval_dataset_name=eval_dataset_name,
        )

        # Generate report
        report = self.evaluator.generate_comparison_report(comparison)

        return {
            "operation": "evaluate",
            "agent_name": agent_name,
            "baseline_model": baseline_model,
            "candidate_model": candidate_model,
            "recommendation": comparison.recommendation,
            "improvement_pct": comparison.improvement_pct,
            "report": report,
            "langsmith_url": comparison.langsmith_experiment_url,
        }

    @traceable(name="modelops_deploy")
    async def _handle_deployment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model deployment request.

        Expected context:
            agent_name: Agent to deploy to
            model_repo: HuggingFace model repo
            deployment_target: openrouter or huggingface
            rollout_strategy: immediate, canary_20pct, or canary_50pct
        """
        agent_name = context.get("agent_name")
        model_repo = context.get("model_repo")
        deployment_target = context.get("deployment_target", "openrouter")
        rollout_strategy = context.get("rollout_strategy", "immediate")

        if not agent_name:
            return {"error": "agent_name required", "context": context}

        if not model_repo:
            return {"error": "model_repo required", "context": context}

        result = await self.deployment.deploy_model_to_agent(
            agent_name=agent_name,
            model_repo=model_repo,
            deployment_target=deployment_target,
            rollout_strategy=rollout_strategy,
        )

        return {
            "operation": "deploy",
            "deployed": result.deployed,
            "agent_name": result.agent_name,
            "model_repo": result.model_repo,
            "version": result.version,
            "rollout_pct": result.rollout_pct,
            "deployed_at": result.deployed_at,
            "config_updated": result.config_path,
            "rollback_available": result.rollback_available,
            "message": f"Deployed {model_repo} to {agent_name} ({result.rollout_pct}% traffic)",
        }

    @traceable(name="modelops_promote_canary")
    async def _handle_canary_promotion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle canary promotion request.

        Expected context:
            agent_name: Agent with canary deployment
            to_percentage: Target percentage (50 or 100)
        """
        agent_name = context.get("agent_name")
        to_percentage = context.get("to_percentage", 100)

        if not agent_name:
            return {"error": "agent_name required", "context": context}

        result = await self.deployment.promote_canary(
            agent_name=agent_name, to_percentage=to_percentage
        )

        return {
            "operation": "promote_canary",
            "agent_name": result.agent_name,
            "model_repo": result.model_repo,
            "version": result.version,
            "rollout_pct": result.rollout_pct,
            "message": f"Promoted canary to {result.rollout_pct}% traffic",
        }

    @traceable(name="modelops_rollback")
    async def _handle_rollback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rollback request.

        Expected context:
            agent_name: Agent to rollback
            to_version: Optional version to rollback to
        """
        agent_name = context.get("agent_name")
        to_version = context.get("to_version")

        if not agent_name:
            return {"error": "agent_name required", "context": context}

        result = await self.deployment.rollback_deployment(
            agent_name=agent_name, to_version=to_version
        )

        return {
            "operation": "rollback",
            "agent_name": result.agent_name,
            "rolled_back_to": result.model_repo,
            "version": result.version,
            "deployed_at": result.deployed_at,
            "message": f"Rolled back {agent_name} to {result.version}",
        }

    @traceable(name="modelops_list_models")
    async def _handle_list_models(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list models request.

        Expected context:
            agent_name: Agent to list models for
            include_archived: Whether to include archived versions
        """
        agent_name = context.get("agent_name")
        include_archived = context.get("include_archived", False)

        if not agent_name:
            return {"error": "agent_name required", "context": context}

        models = await self.deployment.list_agent_models(
            agent_name=agent_name, include_archived=include_archived
        )

        return {
            "operation": "list_models",
            "agent_name": agent_name,
            "count": len(models),
            "models": models,
        }

    @traceable(name="modelops_monitor")
    async def _handle_monitor_training(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle training monitoring request.

        Expected context:
            job_id: Training job ID to monitor
        """
        job_id = context.get("job_id")

        if not job_id:
            return {"error": "job_id required", "context": context}

        result = await self.trainer.monitor_training(job_id)

        return {
            "operation": "monitor",
            "job_id": job_id,
            "status": result.get("status"),
            "progress": result.get("progress"),
            "current_loss": result.get("current_loss"),
            "eta_minutes": result.get("eta_minutes"),
            "trackio_url": result.get("trackio_url"),
        }

    @traceable(name="modelops_status")
    async def _handle_status(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status check request.

        Expected context:
            agent_name: Agent to check status for
        """
        agent_name = context.get("agent_name")

        if not agent_name:
            return {"error": "agent_name required", "context": context}

        current = await self.deployment.get_current_model(agent_name)
        agent_data = self.registry.get_agent(agent_name)

        result = {
            "operation": "status",
            "agent_name": agent_name,
            "current_model": current,
        }

        if agent_data and agent_data.canary:
            result["canary_model"] = {
                "version": agent_data.canary.version,
                "model_id": agent_data.canary.model_id,
                "deployment_status": agent_data.canary.deployment_status,
            }

        return result

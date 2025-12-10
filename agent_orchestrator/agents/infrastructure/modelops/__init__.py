"""ModelOps training module for code-chef infrastructure agent.

Provides fine-tuning capabilities using HuggingFace AutoTrain via Space API.
"""

from .evaluation import EvaluationComparison, ModelEvaluator
from .registry import ModelRegistry, ModelVersion
from .training import ModelOpsTrainer

__all__ = [
    "ModelOpsTrainer",
    "ModelRegistry",
    "ModelVersion",
    "ModelEvaluator",
    "EvaluationComparison",
]

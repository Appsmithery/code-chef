"""ModelOps training module for code-chef infrastructure agent.

Provides fine-tuning capabilities using HuggingFace AutoTrain via Space API.
"""

from .training import ModelOpsTrainer

__all__ = ["ModelOpsTrainer"]

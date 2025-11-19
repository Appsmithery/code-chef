"""
Multi-Agent Workflow Patterns

This package contains standard workflow patterns for multi-agent collaboration:
- Sequential: Agents execute tasks in a predefined order
- Parallel: Agents execute independent subtasks concurrently
- Map-Reduce: Work is distributed to workers and results aggregated
"""

from .sequential import create_sequential_workflow
from .parallel import create_parallel_workflow
from .map_reduce import create_map_reduce_workflow

__all__ = [
    "create_sequential_workflow",
    "create_parallel_workflow",
    "create_map_reduce_workflow"
]

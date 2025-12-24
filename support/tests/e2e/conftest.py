"""
E2E Test Configuration - Path Setup

Configures Python path for pytest to properly resolve agent_orchestrator and shared modules.
This ensures workflow router and other internal imports work correctly in test environment.
"""

import sys
from pathlib import Path

# Calculate project root (4 levels up from this file)
project_root = Path(__file__).parent.parent.parent.parent

# Add critical paths for imports
paths_to_add = [
    project_root,  # Root for top-level imports
    project_root / "agent_orchestrator",  # For workflows.workflow_router
    project_root / "shared",  # For shared.lib imports
]

# Insert at beginning of sys.path (highest priority)
for path in paths_to_add:
    path_str = str(path.resolve())
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# Debug logging (visible with pytest -s)
print(f"[conftest] Project root: {project_root}")
print(f"[conftest] Added {len(paths_to_add)} paths to sys.path")

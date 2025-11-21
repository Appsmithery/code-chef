"""Tests for injecting *_request payloads into the LangGraph workflow."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

# Add paths for imports
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "agent_feature-dev"))
sys.path.insert(0, str(REPO_ROOT / "shared"))

try:
    from service import FeatureRequest
    from services.langgraph.workflow import invoke_workflow
except ImportError:
    # Fallback if imports not available
    FeatureRequest = None
    invoke_workflow = None


class DummyGraph:
    """Minimal stand-in for a compiled LangGraph graph."""

    def __init__(self) -> None:
        self.invocations = []

    def invoke(self, state):  # type: ignore[override]
        self.invocations.append(state)
        return state


def test_feature_request_payload_is_injected():
    graph = DummyGraph()
    feature_request = FeatureRequest(
        description="Implement caching", task_id="task-123"
    )

    result = invoke_workflow(
        graph=graph,
        task_description=feature_request.description,
        request_payloads={"feature_request": feature_request},
    )

    assert graph.invocations, "Graph should be invoked with populated state"
    state = graph.invocations[0]
    assert state["feature_request"]["description"] == feature_request.description
    assert result["feature_request"]["task_id"] == "task-123"


def test_request_key_without_suffix_is_normalized():
    graph = DummyGraph()
    cicd_request = {
        "task_id": "task-456",
        "pipeline_type": "github-actions",
        "stages": ["build", "deploy"],
    }

    invoke_workflow(
        graph=graph,
        task_description="Set up CI/CD",
        request_payloads={"cicd": cicd_request},
    )

    state = graph.invocations[0]
    assert state["cicd_request"]["pipeline_type"] == "github-actions"
    assert state["cicd_request"]["stages"] == ["build", "deploy"]


def test_unknown_request_key_raises_value_error():
    graph = DummyGraph()

    with pytest.raises(ValueError):
        invoke_workflow(
            graph=graph,
            task_description="Unknown",
            request_payloads={"unknown": {"foo": "bar"}},
        )

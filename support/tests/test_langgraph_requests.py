"""Tests for injecting *_request payloads into the LangGraph workflow."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

# Add agent_feature-dev to path (hyphens not allowed in Python imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent_feature-dev"))
from service import FeatureRequest
sys.path.pop(0)

from shared.services.langgraph.workflow import invoke_workflow


class DummyGraph:
    """Minimal stand-in for a compiled LangGraph graph."""

    def __init__(self) -> None:
        self.invocations = []

    def invoke(self, state):  # type: ignore[override]
        self.invocations.append(state)
        return state


def test_feature_request_payload_is_injected():
    graph = DummyGraph()
    feature_request = FeatureRequest(description="Implement caching", task_id="task-123")

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

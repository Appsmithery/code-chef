"""Feature development node implementation."""

from __future__ import annotations

import logging
from langchain_core.messages import HumanMessage
from langchain_core.callbacks.manager import CallbackManagerForChainRun
from pydantic import ValidationError

from agents.feature_dev.service import FeatureRequest, GuardrailViolation, process_feature_request
from agents.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response

logger = logging.getLogger(__name__)


async def feature_dev_node(state: AgentState) -> AgentState:
    """Run the full feature implementation workflow via the shared service layer."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    latest_human = next(
        (msg for msg in reversed(normalized["messages"]) if isinstance(msg, HumanMessage)),
        None,
    )
    request_summary = latest_human.content if latest_human else description

    feature_request: FeatureRequest
    request_payload = normalized.get("feature_request")
    if request_payload:
        try:
            feature_request = FeatureRequest.model_validate(request_payload)
        except ValidationError:
            feature_request = FeatureRequest(
                description=request_payload.get("description", description),
                context_refs=request_payload.get("context_refs"),
                project_context=request_payload.get("project_context"),
                task_id=request_payload.get("task_id") or normalized.get("linear_issue_id"),
            )
    else:
        feature_request = FeatureRequest(
            description=description,
            task_id=normalized.get("linear_issue_id"),
        )

    try:
        response = await process_feature_request(feature_request)
        artifact_paths = ", ".join(artifact.file_path for artifact in response.artifacts[:3])
        if len(response.artifacts) > 3:
            artifact_paths += ", ..."
        content = (
            f"[feature-dev] Completed feature '{response.feature_id}' with status {response.status}. "
            f"Artifacts: {artifact_paths or 'none'}. Commit: {response.commit_message.splitlines()[0]}"
        )

        update = agent_response(normalized, agent_name="feature-dev", content=content)
        update["feature_request"] = feature_request.model_dump(mode="json")
        update["feature_response"] = response.model_dump(mode="json")
        return update
    except GuardrailViolation as exc:
        content = (
            "[feature-dev] Guardrails blocked the request. "
            f"Status: {exc.report.status}. Summary: {exc.report.model_dump(mode='json').get('summary')}"
        )
        update = agent_response(normalized, agent_name="feature-dev", content=content)
        update["guardrail_report"] = exc.report.model_dump(mode="json")
        return update
    except Exception as exc:  # noqa: BLE001
        content = (
            f"[feature-dev] Encountered an unexpected error while processing '{description}': {exc}. "
            f"Latest user input: {request_summary[:180]}"
        )
        update = agent_response(normalized, agent_name="feature-dev", content=content)
        update["error"] = str(exc)
        return update

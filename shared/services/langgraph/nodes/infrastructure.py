"""Infrastructure node implementation backed by the shared service layer."""

from __future__ import annotations

from pydantic import ValidationError
import sys
from pathlib import Path

# Add agent_infrastructure to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "agent_infrastructure"))
from service import (
    GuardrailViolation,
    InfraRequest,
    process_infra_request,
)
sys.path.pop(0)
from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


async def infrastructure_node(state: AgentState) -> AgentState:
    """Generate infrastructure artifacts via the shared service layer."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    request_payload = normalized.get("infrastructure_request")
    requirements = {
        "description": description,
        "rag_context": normalized.get("rag_context", []),
    }

    if request_payload:
        requirements.update(request_payload.get("requirements", {}))

    if request_payload:
        try:
            infra_request = InfraRequest.model_validate({**request_payload, "requirements": requirements})
        except ValidationError:
            infra_request = InfraRequest(
                task_id=request_payload.get("task_id") or normalized.get("linear_issue_id") or "infra-task",
                infrastructure_type=request_payload.get("infrastructure_type", "docker"),
                requirements=requirements,
            )
    else:
        infra_request = InfraRequest(
            task_id=normalized.get("linear_issue_id") or "infra-task",
            infrastructure_type="docker",
            requirements=requirements,
        )

    try:
        response = await process_infra_request(infra_request)
        artifact_paths = ", ".join(artifact.file_path for artifact in response.artifacts[:3]) or "none"
        if len(response.artifacts) > 3:
            artifact_paths += ", ..."
        content = (
            f"[infrastructure] Generated {len(response.artifacts)} artifact(s) for {infra_request.infrastructure_type}. "
            f"Validation={response.validation_status}. Artifacts: {artifact_paths}"
        )

        update = agent_response(normalized, agent_name="infrastructure", content=content)
        update["infrastructure_request"] = infra_request.model_dump(mode="json")
        update["infrastructure_response"] = response.model_dump(mode="json")
        return update
    except GuardrailViolation as exc:
        content = (
            "[infrastructure] Guardrails blocked infra generation. "
            f"Status: {exc.report.status}."
        )
        update = agent_response(normalized, agent_name="infrastructure", content=content)
        update["guardrail_report"] = exc.report.model_dump(mode="json")
        return update
    except Exception as exc:  # noqa: BLE001
        content = (
            f"[infrastructure] Encountered an error while generating infra for '{description}': {exc}."
        )
        update = agent_response(normalized, agent_name="infrastructure", content=content)
        update["error"] = str(exc)
        return update

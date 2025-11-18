"""CI/CD node implementation backed by the shared service layer."""

from __future__ import annotations

from pydantic import ValidationError

from agents.cicd.service import (
    GuardrailViolation,
    PipelineRequest,
    process_pipeline_request,
)
from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


async def cicd_node(state: AgentState) -> AgentState:
    """Generate CI/CD artifacts and record the output in shared state."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    request_payload = normalized.get("cicd_request")
    pipeline_request: PipelineRequest
    if request_payload:
        try:
            pipeline_request = PipelineRequest.model_validate(request_payload)
        except ValidationError:
            pipeline_request = PipelineRequest(
                task_id=request_payload.get("task_id") or normalized.get("linear_issue_id") or "cicd-task",
                pipeline_type=request_payload.get("pipeline_type", "github-actions"),
                stages=request_payload.get("stages") or ["build", "test", "deploy"],
                deployment_strategy=request_payload.get("deployment_strategy"),
            )
    else:
        pipeline_request = PipelineRequest(
            task_id=normalized.get("linear_issue_id") or "cicd-task",
            pipeline_type="github-actions",
            stages=["build", "test", "deploy"],
        )

    try:
        response = await process_pipeline_request(pipeline_request)
        content = (
            f"[cicd] Generated pipeline {response.pipeline_id} for {pipeline_request.pipeline_type}. "
            f"Stages: {', '.join(pipeline_request.stages)}. Validation={response.validation_status}."
        )
        update = agent_response(normalized, agent_name="cicd", content=content)
        update["cicd_request"] = pipeline_request.model_dump(mode="json")
        update["cicd_response"] = response.model_dump(mode="json")
        return update
    except GuardrailViolation as exc:
        content = (
            "[cicd] Guardrails blocked pipeline generation. "
            f"Status: {exc.report.status}."
        )
        update = agent_response(normalized, agent_name="cicd", content=content)
        update["guardrail_report"] = exc.report.model_dump(mode="json")
        return update
    except Exception as exc:  # noqa: BLE001
        content = (
            f"[cicd] Encountered an error while generating CI/CD pipelines for '{description}': {exc}."
        )
        update = agent_response(normalized, agent_name="cicd", content=content)
        update["error"] = str(exc)
        return update

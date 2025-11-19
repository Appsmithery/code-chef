"""Documentation node implementation backed by the shared service layer."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from agent_documentation.service import (
    DocRequest,
    GuardrailViolation,
    process_doc_request,
)
from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


async def documentation_node(state: AgentState) -> AgentState:
    """Generate documentation artifacts using the shared service."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    latest_human = next(
        (msg for msg in reversed(normalized["messages"]) if isinstance(msg, HumanMessage)),
        None,
    )
    inferred_doc_type = "guide" if latest_human and "guide" in latest_human.content.lower() else "readme"

    request_payload = normalized.get("documentation_request")
    doc_request: DocRequest
    if request_payload:
        try:
            doc_request = DocRequest.model_validate(request_payload)
        except ValidationError:
            doc_request = DocRequest(
                task_id=request_payload.get("task_id") or normalized.get("linear_issue_id") or "doc-task",
                doc_type=request_payload.get("doc_type", inferred_doc_type),
                context_refs=request_payload.get("context_refs") or normalized.get("rag_context"),
                target_audience=request_payload.get("target_audience", "developers"),
            )
    else:
        doc_request = DocRequest(
            task_id=normalized.get("linear_issue_id") or "doc-task",
            doc_type=inferred_doc_type,
            context_refs=normalized.get("rag_context", []),
            target_audience="developers",
        )

    try:
        response = await process_doc_request(doc_request)
        content = (
            f"[documentation] Generated documentation set {response.doc_id} for {doc_request.doc_type}. "
            f"Artifacts={len(response.artifacts)}"
        )
        update = agent_response(normalized, agent_name="documentation", content=content)
        update["documentation_request"] = doc_request.model_dump(mode="json")
        update["documentation_response"] = response.model_dump(mode="json")
        return update
    except GuardrailViolation as exc:
        content = (
            "[documentation] Guardrails blocked documentation generation. "
            f"Status: {exc.report.status}."
        )
        update = agent_response(normalized, agent_name="documentation", content=content)
        update["guardrail_report"] = exc.report.model_dump(mode="json")
        return update
    except Exception as exc:  # noqa: BLE001
        content = (
            f"[documentation] Encountered an error while generating docs for '{description}': {exc}."
        )
        update = agent_response(normalized, agent_name="documentation", content=content)
        update["error"] = str(exc)
        return update

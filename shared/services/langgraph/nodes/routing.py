"""Routing helpers for the LangGraph workflow."""

from __future__ import annotations

from typing import Dict, Iterable

from services.langgraph.state import AgentState, ensure_agent_state

AGENT_KEYWORDS: Dict[str, Iterable[str]] = {
    "feature-dev": ("feature", "implement", "build", "add", "refactor"),
    "code-review": ("review", "lint", "quality", "feedback"),
    "infrastructure": ("infrastructure", "iac", "terraform", "deploy", "network"),
    "cicd": ("pipeline", "deploy", "release", "ci", "cd", "tests"),
    "documentation": ("document", "docs", "handbook", "guide", "readme"),
}

COMPLETE_ROUTE = "complete"


def _extract_manual_target(description: str) -> str | None:
    """Allow manual routing hints like `[agent:code-review]` in the description."""

    lowered = description.lower()
    marker = "[agent:"
    if marker not in lowered:
        return None

    start = lowered.index(marker) + len(marker)
    end = lowered.find("]", start)
    if end == -1:
        return None

    candidate = lowered[start:end].strip()
    return candidate if candidate in AGENT_KEYWORDS else None


def classify_task(description: str) -> str:
    """Best-effort classifier that maps descriptions to agents via keyword search."""

    manual_target = _extract_manual_target(description)
    if manual_target:
        return manual_target

    lowered = description.lower()
    for agent, keywords in AGENT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return agent
    return "feature-dev"


def route_task(state: AgentState) -> str:
    """Return the next node label for the LangGraph conditional edge."""

    normalized = ensure_agent_state(state)

    # If another agent has already processed the task, finish for now. This keeps the
    # scaffolding deterministic while we flesh out multi-hop flows later.
    if normalized.get("current_agent") != "orchestrator":
        return COMPLETE_ROUTE

    return classify_task(normalized.get("task_description", ""))

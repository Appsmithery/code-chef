#!/usr/bin/env python3
"""
Update Linear Roadmap with Approval Workflow

This script:
1. Fetches current Linear roadmap issues for AI DevOps Agent Platform project
2. Analyzes completed work and proposes updates
3. Submits update proposal via orchestrator with approval workflow
4. Sends approval notification to @lead-minion in Linear

Usage:
    $env:LINEAR_API_KEY="lin_oauth_..."
    python support/scripts/update-roadmap-with-approvals.py
"""

import os
import sys
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Any

# Linear configuration
LINEAR_API_KEY = os.getenv(
    "LINEAR_API_KEY",
    "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571",
)
LINEAR_PROJECT_ID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "https://codechef.appsmithery.co/api")

# Completed phases based on our work
COMPLETED_WORK = {
    "Phase 2: HITL Integration": {
        "status": "completed",
        "completion_date": "2025-11-13",
        "highlights": [
            "✅ PostgreSQL approval workflow with risk assessment",
            "✅ Orchestrator /orchestrate endpoint with approval gates",
            "✅ Approval/reject APIs with role-based authorization",
            "✅ LangGraph checkpoint integration for workflow resumption",
        ],
    },
    "Phase 5.2: Notification System": {
        "status": "completed",
        "completion_date": "2025-11-18",
        "highlights": [
            "✅ Event bus architecture (async pub/sub)",
            "✅ Linear workspace client with OAuth",
            "✅ Approval notifications to PR-68 hub with @mentions",
            "✅ Sub-second notification latency (<1s)",
            "✅ Email notifier fallback (SMTP optional)",
        ],
    },
    "Phase 8: Repository Reorganization": {
        "status": "completed",
        "completion_date": "2025-11-15",
        "highlights": [
            "✅ Agents moved to root (agent_* prefix)",
            "✅ Shared libraries in shared/lib/",
            "✅ MCP servers in shared/mcp/servers/",
            "✅ Deprecated paths archived",
            "✅ Updated all documentation",
        ],
    },
}

NEXT_PHASES = {
    "Phase 5.3: Approval Decision Notifications": {
        "priority": "medium",
        "tasks": [
            "Subscribe to approval_approved and approval_rejected events",
            'Post decision comments to Linear ("✅ Approved by @user")',
            "Update approval hub issue status on decisions",
            "Add notification analytics (Prometheus metrics)",
        ],
    },
    "Phase 6: Multi-Agent Collaboration": {
        "priority": "high",
        "tasks": [
            "Inter-agent communication via event bus",
            "Shared context propagation across agents",
            "Agent handoff protocols",
            "Workflow coordination for complex tasks",
        ],
    },
}


async def fetch_linear_roadmap() -> List[Dict[str, Any]]:
    """Fetch current roadmap issues from Linear project."""
    query = """
    query GetProjectIssues($projectId: String!) {
        project(id: $projectId) {
            id
            name
            issues {
                nodes {
                    id
                    identifier
                    title
                    description
                    state {
                        name
                        type
                    }
                    priority
                    labels {
                        nodes {
                            name
                        }
                    }
                    updatedAt
                }
            }
        }
    }
    """

    headers = {"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.linear.app/graphql",
            headers=headers,
            json={"query": query, "variables": {"projectId": LINEAR_PROJECT_ID}},
        )
        response.raise_for_status()
        data = response.json()

        return data["data"]["project"]["issues"]["nodes"]


def analyze_completed_work(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze what's been completed and what needs updating."""
    phase2_issue = next((i for i in issues if "Phase 2" in i["title"]), None)
    phase5_issue = next((i for i in issues if "Phase 5" in i["title"]), None)

    updates_needed = []

    # Check Phase 2
    if phase2_issue:
        state = phase2_issue["state"]["name"]
        if state != "Done":
            updates_needed.append(
                {
                    "issue_id": phase2_issue["id"],
                    "identifier": phase2_issue["identifier"],
                    "title": phase2_issue["title"],
                    "current_state": state,
                    "proposed_state": "Done",
                    "reason": "HITL implementation complete with approval workflow and notifications",
                    "evidence": COMPLETED_WORK["Phase 2: HITL Integration"][
                        "highlights"
                    ],
                }
            )

    # Check Phase 5.2
    if phase5_issue:
        state = phase5_issue["state"]["name"]
        needs_update = False

        # Check if notification system mentioned
        description = phase5_issue.get("description", "")
        if "notification system" not in description.lower():
            needs_update = True

        if state not in ["Done", "In Progress"] or needs_update:
            updates_needed.append(
                {
                    "issue_id": phase5_issue["id"],
                    "identifier": phase5_issue["identifier"],
                    "title": phase5_issue["title"],
                    "current_state": state,
                    "proposed_state": (
                        "In Progress" if "5.2" in phase5_issue["title"] else state
                    ),
                    "reason": "Phase 5.2 notification system completed (sub-second latency achieved)",
                    "evidence": COMPLETED_WORK["Phase 5.2: Notification System"][
                        "highlights"
                    ],
                }
            )

    return {
        "updates_needed": updates_needed,
        "completed_phases": list(COMPLETED_WORK.keys()),
        "next_phases": list(NEXT_PHASES.keys()),
    }


async def submit_roadmap_update_for_approval(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Submit roadmap update via orchestrator to trigger approval workflow."""

    # Build update description
    description = "Update Linear roadmap with completed work:\n\n"

    for update in analysis["updates_needed"]:
        description += f"**{update['identifier']}: {update['title']}**\n"
        description += f"- Current: {update['current_state']}\n"
        description += f"- Proposed: {update['proposed_state']}\n"
        description += f"- Reason: {update['reason']}\n\n"
        description += "Evidence:\n"
        for evidence in update["evidence"]:
            description += f"  {evidence}\n"
        description += "\n"

    description += "\n**Completed Phases:**\n"
    for phase in analysis["completed_phases"]:
        highlights = COMPLETED_WORK[phase]["highlights"]
        description += f"\n{phase} ({COMPLETED_WORK[phase]['completion_date']}):\n"
        for highlight in highlights:
            description += f"  {highlight}\n"

    description += "\n**Next Phases:**\n"
    for phase in analysis["next_phases"]:
        tasks = NEXT_PHASES[phase]["tasks"]
        description += f"\n{phase} (Priority: {NEXT_PHASES[phase]['priority']}):\n"
        for task in tasks:
            description += f"  - {task}\n"

    # Submit via orchestrator (will trigger approval for high-priority operations)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/orchestrate",
            json={
                "description": description,
                "priority": "high",  # High priority triggers approval
                "project_context": {
                    "project": "ai-devops-platform",
                    "environment": "production",
                    "operation": "update_linear_roadmap",
                    "target": "Linear roadmap issues",
                },
            },
        )
        response.raise_for_status()
        return response.json()


async def main():
    """Main workflow: fetch roadmap, analyze, submit for approval."""

    print("🔍 Fetching Linear roadmap...")
    issues = await fetch_linear_roadmap()
    print(f"   Found {len(issues)} issues in project")

    print("\n📊 Analyzing completed work...")
    analysis = analyze_completed_work(issues)

    print(f"   ✅ Completed phases: {len(analysis['completed_phases'])}")
    for phase in analysis["completed_phases"]:
        print(f"      - {phase}")

    print(f"\n   📋 Updates needed: {len(analysis['updates_needed'])}")
    for update in analysis["updates_needed"]:
        print(f"      - {update['identifier']}: {update['title']}")
        print(f"        {update['current_state']} → {update['proposed_state']}")

    print(f"\n   🎯 Next phases: {len(analysis['next_phases'])}")
    for phase in analysis["next_phases"]:
        print(f"      - {phase} (Priority: {NEXT_PHASES[phase]['priority']})")

    print("\n🚀 Submitting roadmap update for approval...")
    print(
        "   This will trigger an approval notification to @lead-minion in Linear PR-68"
    )

    try:
        result = await submit_roadmap_update_for_approval(analysis)

        task_id = result.get("task_id")
        status = result.get("routing_plan", {}).get("status")
        approval_id = result.get("routing_plan", {}).get("approval_request_id")

        print(f"\n✅ Roadmap update submitted!")
        print(f"   Task ID: {task_id}")
        print(f"   Status: {status}")

        if approval_id:
            print(f"\n⏳ Approval Required:")
            print(f"   Approval ID: {approval_id}")
            print(f"   Check Linear PR-68 for notification with @lead-minion mention")
            print(f"   Dashboard: {ORCHESTRATOR_URL}/approvals/{approval_id}")
            print(f"\n   To approve:")
            print(f"   task workflow:approve {approval_id}")
            print(f"\n   To reject:")
            print(f'   task workflow:reject {approval_id} REASON="<reason>"')

        print(f"\n📝 Full response:")
        print(json.dumps(result, indent=2))

    except httpx.HTTPStatusError as e:
        print(f"\n❌ Failed to submit roadmap update: {e}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

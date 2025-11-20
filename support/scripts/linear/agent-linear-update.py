#!/usr/bin/env python3
"""
Agent-accessible Linear integration script for ROADMAP UPDATES.

⚠️  IMPORTANT: This script is for PROJECT ROADMAP updates ONLY.
    For HITL approval notifications, use the orchestrator's event bus integration.

ACCESS CONTROL:
- Sub-agents: Update issues in their assigned project only (pass --project-id)
- Orchestrator: Can update any project in Project Roadmaps workspace

This script should be used by agents for roadmap updates to ensure:
1. Proper status management (Todo, In Progress, Done, Cancelled)
2. Sub-issue creation for complex features (break down into 3-5 sub-tasks)
3. Correct project/team association
4. Appropriate metadata and labels

Usage Examples:
    # Create a new phase issue with sub-tasks (AI DevOps Agent Platform)
    python support/scripts/agent-linear-update.py create-phase \
        --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" \
        --phase-number 7 \
        --title "Autonomous Operations" \
        --subtasks "Autonomous Decision Making,Learning from Outcomes,Predictive Task Routing"

    # Update existing issue to mark complete
    python support/scripts/agent-linear-update.py update-status \
        --issue-id "PR-85" \
        --status "done"

    # Create a sub-issue for a feature
    python support/scripts/agent-linear-update.py create-issue \
        --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" \
        --title "Integration Tests Implementation" \
        --parent-id "PR-85-parent-uuid" \
        --status "done"

⚠️  DO NOT USE THIS SCRIPT FOR:
    - HITL approval notifications (use orchestrator event bus → PR-68)
    - Workspace-level approval tracking
    - Cross-project coordination
"""

import os
import sys
import requests
import argparse
from typing import Optional, List, Dict
from datetime import datetime

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("❌ LINEAR_API_KEY environment variable not set")
    sys.exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

# Default project configuration (can be overridden via CLI args)
DEFAULT_PROJECT_UUID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform
DEFAULT_TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"  # Project Roadmaps (PR)

# Known projects in Project Roadmaps workspace
PROJECT_REGISTRY = {
    "ai-devops-agent-platform": {
        "uuid": "b21cbaa1-9f09-40f4-b62a-73e0f86dd501",
        "name": "AI DevOps Agent Platform",
        "slug": "78b3b839d36b"
    },
    "twkr-agentic-resume-workflow": {
        "uuid": "86f8cc40-de06-4e3d-b7c8-ed95193737bc",
        "name": "TWKR Agentic Resume Workflow",
        "slug": "30f6ea5be0a6"
    }
    # Add more projects here as needed
}

# Agent identification for workspace traceability
AGENT_SIGNATURES = {
    "orchestrator": {"tag": "@orchestrator-agent", "name": "🎯 Orchestrator", "signature": "[Orchestrator Agent]"},
    "feature-dev": {"tag": "@feature-dev-agent", "name": "🚀 Feature Dev", "signature": "[Feature-Dev Agent]"},
    "code-review": {"tag": "@code-review-agent", "name": "🔍 Code Review", "signature": "[Code-Review Agent]"},
    "infrastructure": {"tag": "@infrastructure-agent", "name": "🏗️ Infrastructure", "signature": "[Infrastructure Agent]"},
    "cicd": {"tag": "@cicd-agent", "name": "⚙️ CI/CD", "signature": "[CI/CD Agent]"},
    "documentation": {"tag": "@documentation-agent", "name": "📚 Documentation", "signature": "[Documentation Agent]"}
}

# Workflow state IDs (fetched from Linear API on November 19, 2025)
WORKFLOW_STATES = {
    "backlog": "21046e8e-4fc7-4977-82b7-552e501b2f8a",
    "todo": "9b9b5687-666b-4bcb-9ebd-ecf48304a26b",
    "in_progress": "96689f62-1d2c-4db0-8c7a-a2bcba1a61ef",
    "done": "d202b359-862b-4ce5-8b0a-972bf046250a",
    "cancelled": "4d5a61b0-c8a4-449c-91bf-571483a3626f"
}

def get_workflow_states(team_id: str = DEFAULT_TEAM_ID) -> Dict[str, str]:
    """Fetch workflow state IDs for the team.
    
    Args:
        team_id: Linear team ID (default: Project Roadmaps team)
    """
    query = """
    query GetWorkflowStates($teamId: String!) {
        team(id: $teamId) {
            id
            name
            states {
                nodes {
                    id
                    name
                    type
                }
            }
        }
    }
    """
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": query,
            "variables": {"teamId": team_id}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch workflow states: {response.status_code}")
        return {}
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return {}
    
    states = data.get("data", {}).get("team", {}).get("states", {}).get("nodes", [])
    state_map = {}
    
    for state in states:
        state_type = state["type"].lower()
        state_map[state_type] = state["id"]
        print(f"  {state['name']} ({state_type}): {state['id']}")
    
    return state_map

def create_issue(
    title: str,
    description: str,
    project_id: str = DEFAULT_PROJECT_UUID,
    team_id: str = DEFAULT_TEAM_ID,
    status: str = "todo",
    priority: int = 2,
    parent_id: Optional[str] = None,
    labels: Optional[List[str]] = None,
    agent_name: Optional[str] = None
) -> Optional[Dict]:
    """
    Create a new Linear issue in a specific project.
    
    Args:
        title: Issue title
        description: Issue description (Markdown supported)
        project_id: Linear project UUID (default: AI DevOps Agent Platform)
        team_id: Linear team ID (default: Project Roadmaps)
        status: One of: backlog, todo, in_progress, done, cancelled
        priority: 0 (no priority), 1 (urgent), 2 (high), 3 (normal), 4 (low)
        parent_id: Parent issue ID if creating a sub-issue
        labels: List of label names to apply
        agent_name: Agent identifier for workspace traceability (e.g., 'orchestrator', 'feature-dev')
    
    Returns:
        Created issue data or None if failed
    """
    # Add agent signature to description for traceability
    if agent_name and agent_name in AGENT_SIGNATURES:
        agent_info = AGENT_SIGNATURES[agent_name]
        signature = f"\n\n---\n*Created by {agent_info['name']} {agent_info['signature']}*\n*Agent Tag: {agent_info['tag']}*"
        description = description + signature
    # Get the correct state ID
    if status not in WORKFLOW_STATES:
        print(f"⚠️  Unknown status '{status}', using 'todo'")
        status = "todo"
    
    state_id = WORKFLOW_STATES.get(status)
    if not state_id or state_id.endswith("-state-id"):
        print("⚠️  Workflow states not initialized. Fetching...")
        states = get_workflow_states()
        if status in states:
            state_id = states[status]
        else:
            print(f"❌ Could not find state ID for '{status}'")
            return None
    
    mutation = """
    mutation CreateIssue(
        $teamId: String!,
        $projectId: String!,
        $title: String!,
        $description: String!,
        $stateId: String!,
        $priority: Int!,
        $parentId: String
    ) {
        issueCreate(
            input: {
                teamId: $teamId
                projectId: $projectId
                title: $title
                description: $description
                stateId: $stateId
                priority: $priority
                parentId: $parentId
            }
        ) {
            success
            issue {
                id
                identifier
                title
                url
                state {
                    name
                }
            }
        }
    }
    """
    
    variables = {
        "teamId": team_id,
        "projectId": project_id,
        "title": title,
        "description": description,
        "stateId": state_id,
        "priority": priority
    }
    
    if parent_id:
        variables["parentId"] = parent_id
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": mutation,
            "variables": variables
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create issue: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return None
    
    result = data.get("data", {}).get("issueCreate", {})
    if result.get("success"):
        issue = result.get("issue", {})
        print(f"✅ Created: {issue.get('identifier')} - {issue.get('title')}")
        print(f"   Status: {issue.get('state', {}).get('name')}")
        print(f"   URL: {issue.get('url')}")
        return issue
    
    return None

def update_issue_status(issue_identifier: str, status: str) -> bool:
    """
    Update an issue's status.
    
    Args:
        issue_identifier: Issue identifier (e.g., 'PR-85')
        status: One of: backlog, todo, in_progress, done, cancelled
    
    Returns:
        True if successful, False otherwise
    """
    # First, get the issue ID from identifier
    query = """
    query GetIssue($issueId: String!) {
        issue(id: $issueId) {
            id
            identifier
            title
        }
    }
    """
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": query,
            "variables": {"issueId": issue_identifier}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch issue: {response.status_code}")
        return False
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return False
    
    issue = data.get("data", {}).get("issue")
    if not issue:
        print(f"❌ Issue {issue_identifier} not found")
        return False
    
    issue_id = issue["id"]
    
    # Get the correct state ID
    if status not in WORKFLOW_STATES or WORKFLOW_STATES[status].endswith("-state-id"):
        states = get_workflow_states()
        if status not in states:
            print(f"❌ Status '{status}' not found")
            return False
        state_id = states[status]
    else:
        state_id = WORKFLOW_STATES[status]
    
    # Update the issue
    mutation = """
    mutation UpdateIssue($issueId: String!, $stateId: String!) {
        issueUpdate(
            id: $issueId,
            input: { stateId: $stateId }
        ) {
            success
            issue {
                identifier
                title
                state {
                    name
                }
            }
        }
    }
    """
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": mutation,
            "variables": {
                "issueId": issue_id,
                "stateId": state_id
            }
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to update issue: {response.status_code}")
        return False
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return False
    
    result = data.get("data", {}).get("issueUpdate", {})
    if result.get("success"):
        issue = result.get("issue", {})
        print(f"✅ Updated {issue.get('identifier')} to '{issue.get('state', {}).get('name')}'")
        return True
    
    return False

def create_phase_with_subtasks(
    phase_number: int,
    title: str,
    description: str,
    subtasks: List[str],
    project_id: str = DEFAULT_PROJECT_UUID,
    team_id: str = DEFAULT_TEAM_ID,
    status: str = "todo",
    agent_name: Optional[str] = None
) -> Optional[str]:
    """
    Create a phase issue with sub-tasks in a specific project.
    
    Args:
        phase_number: Phase number (e.g., 7)
        title: Phase title (e.g., "Autonomous Operations")
        description: Phase description
        subtasks: List of subtask titles (3-5 recommended)
        project_id: Linear project UUID (default: AI DevOps Agent Platform)
        team_id: Linear team ID (default: Project Roadmaps)
        status: Initial status (default: todo)
        agent_name: Agent identifier for workspace traceability
    
    Returns:
        Parent issue ID if successful, None otherwise
    """
    # Create parent issue
    full_title = f"Phase {phase_number}: {title}"
    parent = create_issue(
        title=full_title,
        description=description,
        project_id=project_id,
        team_id=team_id,
        status=status,
        priority=1,  # High priority for phases
        agent_name=agent_name
    )
    
    if not parent:
        return None
    
    parent_id = parent["id"]
    
    # Create sub-tasks
    print(f"\n📋 Creating {len(subtasks)} sub-tasks...")
    for i, subtask_title in enumerate(subtasks, 1):
        subtask_desc = f"Subtask {i} of {len(subtasks)} for {full_title}"
        subissue = create_issue(
            title=f"Task {phase_number}.{i}: {subtask_title}",
            description=subtask_desc,
            project_id=project_id,
            team_id=team_id,
            status="todo",
            priority=2,
            parent_id=parent_id,
            agent_name=agent_name
        )
        
        if subissue:
            print(f"  ✅ Created sub-task {i}/{len(subtasks)}")
    
    print(f"\n✨ Phase {phase_number} created with {len(subtasks)} sub-tasks!")
    return parent_id

def main():
    parser = argparse.ArgumentParser(
        description="Agent-accessible Linear integration for creating/updating issues"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Get workflow states command
    parser_states = subparsers.add_parser("get-states", help="Fetch workflow state IDs")
    parser_states.add_argument("--team-id", help="Linear team ID (default: Project Roadmaps)")
    
    # Create issue command
    parser_create = subparsers.add_parser("create-issue", help="Create a new issue")
    parser_create.add_argument("--title", required=True, help="Issue title")
    parser_create.add_argument("--description", required=True, help="Issue description")
    parser_create.add_argument("--project-id", help="Linear project UUID (default: AI DevOps Agent Platform)")
    parser_create.add_argument("--team-id", help="Linear team ID (default: Project Roadmaps)")
    parser_create.add_argument("--status", default="todo", choices=["backlog", "todo", "in_progress", "done", "cancelled"])
    parser_create.add_argument("--priority", type=int, default=2, choices=[0, 1, 2, 3, 4])
    parser_create.add_argument("--parent-id", help="Parent issue ID for sub-issues")
    parser_create.add_argument("--agent-name", help="Agent identifier for traceability (orchestrator, feature-dev, etc.)")
    
    # Create phase command
    parser_phase = subparsers.add_parser("create-phase", help="Create a phase with sub-tasks")
    parser_phase.add_argument("--phase-number", type=int, required=True, help="Phase number (e.g., 7)")
    parser_phase.add_argument("--title", required=True, help="Phase title")
    parser_phase.add_argument("--description", required=True, help="Phase description")
    parser_phase.add_argument("--subtasks", required=True, help="Comma-separated subtask titles")
    parser_phase.add_argument("--project-id", help="Linear project UUID (default: AI DevOps Agent Platform)")
    parser_phase.add_argument("--team-id", help="Linear team ID (default: Project Roadmaps)")
    parser_phase.add_argument("--status", default="todo", choices=["backlog", "todo", "in_progress", "done", "cancelled"])
    parser_phase.add_argument("--agent-name", help="Agent identifier for traceability (orchestrator, feature-dev, etc.)")
    
    # Update status command
    parser_update = subparsers.add_parser("update-status", help="Update issue status")
    parser_update.add_argument("--issue-id", required=True, help="Issue identifier (e.g., PR-85)")
    parser_update.add_argument("--status", required=True, choices=["backlog", "todo", "in_progress", "done", "cancelled"])
    
    args = parser.parse_args()
    
    if args.command == "get-states":
        print("\n📊 Fetching workflow states...\n")
        team_id = args.team_id if args.team_id else DEFAULT_TEAM_ID
        states = get_workflow_states(team_id)
        if states:
            print("\n✅ Workflow states fetched successfully")
            print("\nUpdate WORKFLOW_STATES in this script with these IDs:")
            for status, state_id in states.items():
                print(f'    "{status}": "{state_id}",')
    
    elif args.command == "create-issue":
        project_id = args.project_id if args.project_id else DEFAULT_PROJECT_UUID
        team_id = args.team_id if args.team_id else DEFAULT_TEAM_ID
        agent_name = args.agent_name if hasattr(args, 'agent_name') and args.agent_name else None
        create_issue(
            title=args.title,
            description=args.description,
            project_id=project_id,
            team_id=team_id,
            status=args.status,
            priority=args.priority,
            parent_id=args.parent_id,
            agent_name=agent_name
        )
    
    elif args.command == "create-phase":
        project_id = args.project_id if args.project_id else DEFAULT_PROJECT_UUID
        team_id = args.team_id if args.team_id else DEFAULT_TEAM_ID
        agent_name = args.agent_name if hasattr(args, 'agent_name') and args.agent_name else None
        subtasks = [s.strip() for s in args.subtasks.split(",")]
        if len(subtasks) < 3:
            print("⚠️  Recommendation: Create at least 3 sub-tasks for better context")
        create_phase_with_subtasks(
            phase_number=args.phase_number,
            title=args.title,
            description=args.description,
            subtasks=subtasks,
            project_id=project_id,
            team_id=team_id,
            status=args.status,
            agent_name=agent_name
        )
    
    elif args.command == "update-status":
        update_issue_status(
            issue_identifier=args.issue_id,
            status=args.status
        )
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

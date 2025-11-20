#!/usr/bin/env python3
"""
Agent-accessible Linear integration script for creating and updating issues.

This script should be used by agents for ALL Linear updates to ensure:
1. Proper status management (Todo, In Progress, Done, Cancelled)
2. Sub-issue creation for complex features (break down into 3-5 sub-tasks)
3. Correct project/team association
4. Appropriate metadata and labels

Usage Examples:
    # Create a new phase issue with sub-tasks
    python support/scripts/agent-linear-update.py create-phase \
        --title "Phase 7: Autonomous Operations" \
        --status "todo" \
        --subtasks "Autonomous Decision Making,Learning from Outcomes,Predictive Task Routing"

    # Update existing issue to mark complete
    python support/scripts/agent-linear-update.py update-issue \
        --issue-id "PR-85" \
        --status "done" \
        --add-completion-notes

    # Create a sub-issue for a feature
    python support/scripts/agent-linear-update.py create-subissue \
        --parent-id "PR-85" \
        --title "Integration Tests Implementation" \
        --status "done"
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

# Project configuration
PROJECT_UUID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform
TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"  # Project Roadmaps (PR)

# Workflow state IDs (fetched from Linear API on November 19, 2025)
WORKFLOW_STATES = {
    "backlog": "21046e8e-4fc7-4977-82b7-552e501b2f8a",
    "todo": "9b9b5687-666b-4bcb-9ebd-ecf48304a26b",
    "in_progress": "96689f62-1d2c-4db0-8c7a-a2bcba1a61ef",
    "done": "d202b359-862b-4ce5-8b0a-972bf046250a",
    "cancelled": "4d5a61b0-c8a4-449c-91bf-571483a3626f"
}

def get_workflow_states() -> Dict[str, str]:
    """Fetch workflow state IDs for the team."""
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
            "variables": {"teamId": TEAM_ID}
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
    status: str = "todo",
    priority: int = 2,
    parent_id: Optional[str] = None,
    labels: Optional[List[str]] = None
) -> Optional[Dict]:
    """
    Create a new Linear issue.
    
    Args:
        title: Issue title
        description: Issue description (Markdown supported)
        status: One of: backlog, todo, in_progress, done, cancelled
        priority: 0 (no priority), 1 (urgent), 2 (high), 3 (normal), 4 (low)
        parent_id: Parent issue ID if creating a sub-issue
        labels: List of label names to apply
    
    Returns:
        Created issue data or None if failed
    """
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
        "teamId": TEAM_ID,
        "projectId": PROJECT_UUID,
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
    status: str = "todo"
) -> Optional[str]:
    """
    Create a phase issue with sub-tasks.
    
    Args:
        phase_number: Phase number (e.g., 7)
        title: Phase title (e.g., "Autonomous Operations")
        description: Phase description
        subtasks: List of subtask titles (3-5 recommended)
        status: Initial status (default: todo)
    
    Returns:
        Parent issue ID if successful, None otherwise
    """
    # Create parent issue
    full_title = f"Phase {phase_number}: {title}"
    parent = create_issue(
        title=full_title,
        description=description,
        status=status,
        priority=1  # High priority for phases
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
            status="todo",
            priority=2,
            parent_id=parent_id
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
    
    # Create issue command
    parser_create = subparsers.add_parser("create-issue", help="Create a new issue")
    parser_create.add_argument("--title", required=True, help="Issue title")
    parser_create.add_argument("--description", required=True, help="Issue description")
    parser_create.add_argument("--status", default="todo", choices=["backlog", "todo", "in_progress", "done", "cancelled"])
    parser_create.add_argument("--priority", type=int, default=2, choices=[0, 1, 2, 3, 4])
    parser_create.add_argument("--parent-id", help="Parent issue ID for sub-issues")
    
    # Create phase command
    parser_phase = subparsers.add_parser("create-phase", help="Create a phase with sub-tasks")
    parser_phase.add_argument("--phase-number", type=int, required=True, help="Phase number (e.g., 7)")
    parser_phase.add_argument("--title", required=True, help="Phase title")
    parser_phase.add_argument("--description", required=True, help="Phase description")
    parser_phase.add_argument("--subtasks", required=True, help="Comma-separated subtask titles")
    parser_phase.add_argument("--status", default="todo", choices=["backlog", "todo", "in_progress", "done", "cancelled"])
    
    # Update status command
    parser_update = subparsers.add_parser("update-status", help="Update issue status")
    parser_update.add_argument("--issue-id", required=True, help="Issue identifier (e.g., PR-85)")
    parser_update.add_argument("--status", required=True, choices=["backlog", "todo", "in_progress", "done", "cancelled"])
    
    args = parser.parse_args()
    
    if args.command == "get-states":
        print("\n📊 Fetching workflow states...\n")
        states = get_workflow_states()
        if states:
            print("\n✅ Workflow states fetched successfully")
            print("\nUpdate WORKFLOW_STATES in this script with these IDs:")
            for status, state_id in states.items():
                print(f'    "{status}": "{state_id}",')
    
    elif args.command == "create-issue":
        create_issue(
            title=args.title,
            description=args.description,
            status=args.status,
            priority=args.priority,
            parent_id=args.parent_id
        )
    
    elif args.command == "create-phase":
        subtasks = [s.strip() for s in args.subtasks.split(",")]
        if len(subtasks) < 3:
            print("⚠️  Recommendation: Create at least 3 sub-tasks for better context")
        create_phase_with_subtasks(
            phase_number=args.phase_number,
            title=args.title,
            description=args.description,
            subtasks=subtasks,
            status=args.status
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

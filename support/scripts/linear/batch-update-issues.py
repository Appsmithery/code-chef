#!/usr/bin/env python3
"""
Batch update Linear issues for CHEF project.
Updates status and priority for multiple issues.
"""

import os
import sys
import requests
from typing import Optional, Dict, Any

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("❌ LINEAR_API_KEY environment variable not set")
    sys.exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"
TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"  # Project Roadmaps (CHEF)


def graphql_request(query: str, variables: Dict[str, Any] = None) -> Dict:
    """Execute a GraphQL request to Linear API."""
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": query,
            "variables": variables or {}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ HTTP Error: {response.status_code}")
        print(response.text)
        return {}
    
    return response.json()


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
    
    data = graphql_request(query, {"teamId": TEAM_ID})
    
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return {}
    
    states = data.get("data", {}).get("team", {}).get("states", {}).get("nodes", [])
    state_map = {}
    
    print("=== Workflow States ===")
    for state in states:
        name_lower = state["name"].lower().replace(" ", "_")
        state_map[name_lower] = state["id"]
        state_map[state["name"]] = state["id"]  # Also map by exact name
        print(f"  {state['name']}: {state['id']} (type: {state['type']})")
    
    return state_map


def get_issue_id(identifier: str) -> Optional[str]:
    """Get the internal UUID for an issue by its identifier."""
    query = """
    query GetIssue($issueId: String!) {
        issue(id: $issueId) {
            id
            identifier
            title
            state {
                name
            }
            priority
        }
    }
    """
    
    data = graphql_request(query, {"issueId": identifier})
    
    if "errors" in data:
        print(f"❌ Error fetching {identifier}: {data['errors']}")
        return None
    
    issue = data.get("data", {}).get("issue")
    if issue:
        print(f"  Found: {issue['identifier']} - {issue['title']}")
        print(f"    Current state: {issue['state']['name']}, Priority: {issue['priority']}")
        return issue["id"]
    
    print(f"❌ Issue {identifier} not found")
    return None


def update_issue(issue_id: str, state_id: str = None, priority: int = None) -> bool:
    """Update an issue's state and/or priority."""
    input_fields = {}
    if state_id:
        input_fields["stateId"] = state_id
    if priority is not None:
        input_fields["priority"] = priority
    
    if not input_fields:
        print("  ⚠️ No updates specified")
        return False
    
    # Build dynamic mutation based on what we're updating
    mutation = """
    mutation UpdateIssue($issueId: String!, $input: IssueUpdateInput!) {
        issueUpdate(id: $issueId, input: $input) {
            success
            issue {
                identifier
                title
                state {
                    name
                }
                priority
            }
        }
    }
    """
    
    data = graphql_request(mutation, {
        "issueId": issue_id,
        "input": input_fields
    })
    
    if "errors" in data:
        print(f"❌ Update failed: {data['errors']}")
        return False
    
    result = data.get("data", {}).get("issueUpdate", {})
    if result.get("success"):
        issue = result.get("issue", {})
        print(f"  ✅ Updated {issue.get('identifier')} → State: {issue.get('state', {}).get('name')}, Priority: {issue.get('priority')}")
        return True
    
    return False


def main():
    print("=" * 60)
    print("BATCH LINEAR ISSUE UPDATES")
    print("=" * 60)
    
    # Step 1: Get workflow states
    print("\n📋 Fetching workflow states...")
    states = get_workflow_states()
    
    if not states:
        print("❌ Could not fetch workflow states")
        sys.exit(1)
    
    in_progress_id = states.get("In Progress") or states.get("in_progress")
    canceled_id = states.get("Canceled") or states.get("cancelled") or states.get("Cancelled")
    
    if not in_progress_id:
        print("❌ Could not find 'In Progress' state")
        sys.exit(1)
    
    if not canceled_id:
        print("❌ Could not find 'Canceled' state")
        sys.exit(1)
    
    print(f"\n📌 State IDs:")
    print(f"  In Progress: {in_progress_id}")
    print(f"  Canceled: {canceled_id}")
    
    # Step 2: Update CHEF-112 to "In Progress"
    print("\n" + "=" * 60)
    print("1️⃣ UPDATE CHEF-112 → In Progress")
    print("=" * 60)
    issue_id = get_issue_id("CHEF-112")
    if issue_id:
        update_issue(issue_id, state_id=in_progress_id)
    
    # Step 3: Cancel CHEF-111
    print("\n" + "=" * 60)
    print("2️⃣ CANCEL CHEF-111")
    print("=" * 60)
    issue_id = get_issue_id("CHEF-111")
    if issue_id:
        update_issue(issue_id, state_id=canceled_id)
    
    # Step 4: Cancel CHEF-116, CHEF-117, CHEF-93
    print("\n" + "=" * 60)
    print("3️⃣ CANCEL CHEF-116, CHEF-117, CHEF-93")
    print("=" * 60)
    
    for identifier in ["CHEF-116", "CHEF-117", "CHEF-93"]:
        print(f"\n  Processing {identifier}...")
        issue_id = get_issue_id(identifier)
        if issue_id:
            update_issue(issue_id, state_id=canceled_id)
    
    # Step 5: Reprioritize CHEF-118 from Urgent (1) to High (2)
    print("\n" + "=" * 60)
    print("4️⃣ REPRIORITIZE CHEF-118 → High (2)")
    print("=" * 60)
    issue_id = get_issue_id("CHEF-118")
    if issue_id:
        update_issue(issue_id, priority=2)
    
    print("\n" + "=" * 60)
    print("✅ BATCH UPDATE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

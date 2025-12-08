#!/usr/bin/env python3
"""Update CHEF-110 and CHEF-118 to In Progress status."""

import os
import sys
import requests

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("❌ LINEAR_API_KEY environment variable not set")
    sys.exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"
TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"


def graphql_request(query, variables=None):
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}}
    )
    return response.json()


def main():
    # Step 1: Get workflow states
    query = """
    query GetWorkflowStates($teamId: String!) {
        team(id: $teamId) {
            states { nodes { id name type } }
        }
    }
    """
    data = graphql_request(query, {"teamId": TEAM_ID})
    states = data.get("data", {}).get("team", {}).get("states", {}).get("nodes", [])
    in_progress_id = next((s["id"] for s in states if s["name"] == "In Progress"), None)
    print(f"In Progress state ID: {in_progress_id}")

    if not in_progress_id:
        print("❌ Could not find 'In Progress' state")
        sys.exit(1)

    # Step 2: Update both issues
    for identifier in ["CHEF-110", "CHEF-118"]:
        print(f"\n📋 Processing {identifier}...")
        
        # Get issue
        get_query = f'query {{ issue(id: "{identifier}") {{ id identifier title state {{ name }} }} }}'
        data = graphql_request(get_query)
        issue = data.get("data", {}).get("issue")
        
        if issue:
            print(f"  Found: {issue['identifier']} - {issue['title']}")
            print(f"  Current state: {issue['state']['name']}")
            
            # Update issue
            mutation = """
            mutation UpdateIssue($issueId: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $issueId, input: $input) {
                    success
                    issue { identifier title state { name } }
                }
            }
            """
            result = graphql_request(mutation, {
                "issueId": issue["id"],
                "input": {"stateId": in_progress_id}
            })
            
            update = result.get("data", {}).get("issueUpdate", {})
            if update.get("success"):
                updated_issue = update.get("issue", {})
                print(f"  ✅ Updated → {updated_issue['state']['name']}")
            else:
                print(f"  ❌ Failed: {result}")
        else:
            print(f"  ❌ Issue {identifier} not found")

    print("\n" + "=" * 50)
    print("✅ CHEF-110 and CHEF-118 updated to In Progress")
    print("=" * 50)


if __name__ == "__main__":
    main()

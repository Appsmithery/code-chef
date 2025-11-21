#!/usr/bin/env python3
"""
Extract Linear Custom Field IDs from Template Issue
Creates a test issue from the HITL template and extracts custom field IDs from the response.

Usage:
    python support/scripts/linear/extract-custom-field-ids.py

Environment:
    LINEAR_API_KEY: Linear OAuth token
    LINEAR_APPROVAL_HUB_ISSUE_ID: Parent issue ID (DEV-68)
"""

import os
import sys
import json
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


def extract_custom_fields():
    """Create test issue and extract custom field IDs from GraphQL response"""

    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("ERROR: LINEAR_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    parent_issue_id = os.getenv("LINEAR_APPROVAL_HUB_ISSUE_ID", "DEV-68")
    template_id = "8881211a-7b9c-42ab-a178-608ddf1f6665"

    transport = RequestsHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": api_key},
        verify=True,
        retries=3,
    )

    client = Client(transport=transport, fetch_schema_from_transport=True)

    print(f"Creating test issue from template {template_id}...")
    print()

    # Create issue from template
    create_mutation = gql(
        """
        mutation CreateIssueFromTemplate($templateId: String!, $teamId: String!, $title: String!, $description: String, $parentId: String) {
            issueCreate(input: {
                templateId: $templateId
                teamId: $teamId
                title: $title
                description: $description
                parentId: $parentId
            }) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
    """
    )

    # Get team ID first
    teams_query = gql(
        """
        query GetTeams {
            teams {
                nodes {
                    id
                    key
                    name
                }
            }
        }
    """
    )

    teams_result = client.execute(teams_query)
    dev_team = next(
        (t for t in teams_result["teams"]["nodes"] if t["key"] == "DEV"), None
    )

    if not dev_team:
        print("ERROR: DEV team not found", file=sys.stderr)
        sys.exit(1)

    # Get parent issue ID - Linear API requires full UUID, not identifier
    # For now, let's skip parent linking and just create a standalone issue
    # You can manually link it after creation
    parent_id = None  # We'll create without parent, then manually link in UI

    # Create test issue
    create_result = client.execute(
        create_mutation,
        variable_values={
            "templateId": template_id,
            "teamId": dev_team["id"],
            "title": "[TEST] Custom Field Extraction",
            "description": "Temporary issue to extract custom field IDs. Safe to delete.",
            "parentId": parent_id,
        },
    )

    if not create_result["issueCreate"]["success"]:
        print("ERROR: Failed to create issue", file=sys.stderr)
        sys.exit(1)

    issue = create_result["issueCreate"]["issue"]
    print(f"✓ Created test issue: {issue['identifier']}")
    print(f"  URL: {issue['url']}")
    print()

    # Now query the issue with full details to get custom fields
    issue_query = gql(
        """
        query GetIssueWithCustomFields($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                customFields {
                    id
                    name
                    type
                    value
                }
            }
        }
    """
    )

    print("Fetching custom field details...")
    issue_result = client.execute(issue_query, variable_values={"id": issue["id"]})

    custom_fields = issue_result["issue"].get("customFields", [])

    if not custom_fields:
        print("WARNING: No custom fields found on issue", file=sys.stderr)
        print("This might mean:")
        print("  1. Template doesn't have custom fields configured")
        print("  2. Custom fields API changed")
        print("  3. Custom fields not exposed via GraphQL")
        print()
        print("Try inspecting the issue in Linear's web UI with DevTools:")
        print(f"  {issue['url']}")
        sys.exit(1)

    print()
    print("Found Custom Fields:")
    print("=" * 80)

    env_vars = []

    for field in custom_fields:
        print(f"\nField: {field['name']}")
        print(f"  ID: {field['id']}")
        print(f"  Type: {field['type']}")
        if field.get("value"):
            print(f"  Current Value: {field['value']}")

        # Generate env var name
        env_var_name = f"LINEAR_FIELD_{field['name'].upper().replace(' ', '_').replace('-', '_')}_ID"
        env_vars.append(f"{env_var_name}={field['id']}")

    print()
    print("=" * 80)
    print("Environment Configuration:")
    print("=" * 80)
    for var in env_vars:
        print(var)

    print()
    print(f"✓ Custom field extraction complete")
    print(f"✓ Test issue created: {issue['identifier']}")
    print(f"  You can delete this test issue from: {issue['url']}")

    return issue["identifier"]


if __name__ == "__main__":
    try:
        issue_id = extract_custom_fields()
        print()
        print("Next steps:")
        print("  1. Copy the environment variables above to config/env/.env")
        print("  2. Delete the test issue from Linear")
        print(
            "  3. Deploy configuration: ./support/scripts/deploy/deploy-to-droplet.ps1 -DeployType config"
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)

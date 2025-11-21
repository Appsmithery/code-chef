#!/usr/bin/env python3
"""
Linear Custom Fields Inspector (Manual Extraction Guide)

Linear's GraphQL API doesn't expose custom field schemas directly.
Custom fields are template-specific and must be extracted from actual issues.

This script guides you through the manual extraction process.

Usage:
    python support/scripts/linear/get-custom-fields.py <ISSUE_ID>

Example:
    python support/scripts/linear/get-custom-fields.py DEV-134

Environment:
    LINEAR_API_KEY: Linear API token (OAuth or Personal Access Token)

Output:
    Prints custom field IDs from the specified issue
    Copy values to config/env/.env for LINEAR_FIELD_*_ID variables
"""

import os
import sys
import json
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


def get_custom_fields_from_issue(issue_id: str):
    """Extract custom fields from an existing issue created from template"""

    # Setup GraphQL client
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("ERROR: LINEAR_API_KEY environment variable not set", file=sys.stderr)
        print("Get your API key from: https://linear.app/settings/api", file=sys.stderr)
        sys.exit(1)

    transport = RequestsHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": api_key},
        verify=True,
        retries=3,
    )

    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Query the issue to inspect its custom fields
    # Note: Linear API doesn't have a standard customFields connection
    # Custom fields are stored as arbitrary JSON in the issue data
    issue_query = gql(
        """
        query GetIssue($issueId: String!) {
            issue(id: $issueId) {
                id
                identifier
                title
                description
                state {
                    id
                    name
                }
            }
        }
    """
    )

    try:
        result = client.execute(issue_query, variable_values={"issueId": issue_id})
        issue = result["issue"]

        print(f"Issue: {issue['identifier']} - {issue['title']}")
        print("=" * 80)
        print()
        print("NOTE: Linear API limitation - custom fields not directly exposed")
        print()
        print("Manual extraction required:")
        print()
        print("  1. Open issue in Linear app:")
        print(f"     https://linear.app/dev-ops/issue/{issue['identifier']}")
        print()
        print("  2. Open browser DevTools (F12) → Network tab")
        print()
        print("  3. Refresh the page, find GraphQL request for 'Issue'")
        print()
        print("  4. Look in response JSON for custom field data")
        print()
        print("  5. Custom fields typically appear as:")
        print("     - Direct properties on issue object")
        print("     - Nested under 'customFields' or 'metadata'")
        print()
        print("Alternative: Use Linear's browser extension inspection")
        print("=" * 80)
        print()
        print("Based on your template screenshot, expected fields:")
        print()
        print("  Field: Request Status")
        print("    Type: Dropdown (single select)")
        print("    Options: Approved, Denied, More information required")
        print()
        print("  Field: Required Action")
        print("    Type: Checkboxes (multi-select)")
        print("    Options: Review proposed changes, Verify risks are acceptable,")
        print("             Check implementation approach, Request modifications")
        print()
        print("Once you extract the field IDs, add to config/env/.env:")
        print()
        print("  LINEAR_FIELD_REQUEST_STATUS_ID=<field_id_from_inspection>")
        print("  LINEAR_FIELD_REQUIRED_ACTION_ID=<field_id_from_inspection>")

    except Exception as e:
        print(f"ERROR querying issue: {e}", file=sys.stderr)
        print()
        print("Make sure the issue ID is correct and accessible.")
        print("Try format: 'DEV-123' or use the full UUID")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Linear Custom Fields Inspector")
        print("=" * 80)
        print()
        print("Usage: python get-custom-fields.py <ISSUE_ID>")
        print()
        print("Example: python get-custom-fields.py DEV-134")
        print()
        print("This script helps extract custom field IDs from Linear issues.")
        print("Create a test issue from your template first, then inspect it.")
        print()
        sys.exit(1)

    issue_id = sys.argv[1]

    try:
        get_custom_fields_from_issue(issue_id)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

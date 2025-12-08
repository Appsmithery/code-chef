#!/usr/bin/env python3
"""
Fetch all open Linear issues for the Code-Chef project.
Generates a comprehensive report of open issues, sub-issues, and recommendations.
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

# Try LINEAR_CHEF_API_KEY first (Personal API Key), fall back to LINEAR_API_KEY (OAuth)
LINEAR_API_KEY = os.environ.get("LINEAR_CHEF_API_KEY") or os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("ERROR: LINEAR_CHEF_API_KEY or LINEAR_API_KEY environment variable not set")
    sys.exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"
PROJECT_UUID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform

# Define stale threshold (7 days)
STALE_DAYS = 7


def fetch_open_issues():
    """Fetch all open issues from the project."""
    query = """
    query GetOpenIssues($projectId: ID!) {
      issues(
        filter: {
          project: {id: {eq: $projectId}}
          state: {type: {nin: ["completed", "canceled"]}}
        }
        first: 100
        orderBy: updatedAt
      ) {
        nodes {
          id
          identifier
          title
          description
          state {
            id
            name
            type
          }
          priority
          priorityLabel
          assignee {
            name
            email
          }
          updatedAt
          createdAt
          url
          parent {
            id
            identifier
            title
          }
          children {
            nodes {
              id
              identifier
              title
              state {
                name
                type
              }
              priority
              priorityLabel
              updatedAt
            }
          }
          labels {
            nodes {
              id
              name
            }
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
            "variables": {"projectId": PROJECT_UUID}
        }
    )

    if response.status_code != 200:
        print(f"ERROR: {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    if "errors" in data:
        print(f"GraphQL Errors: {json.dumps(data['errors'], indent=2)}")
        return None

    return data.get("data", {}).get("issues", {}).get("nodes", [])


def fetch_all_project_issues():
    """Fetch ALL issues (including completed) for comprehensive view."""
    query = """
    query GetAllProjectIssues($projectId: ID!) {
      issues(
        filter: {
          project: {id: {eq: $projectId}}
        }
        first: 200
        orderBy: updatedAt
      ) {
        nodes {
          id
          identifier
          title
          state {
            id
            name
            type
          }
          priority
          priorityLabel
          assignee {
            name
            email
          }
          updatedAt
          createdAt
          url
          parent {
            id
            identifier
            title
          }
          children {
            nodes {
              id
              identifier
              title
              state {
                name
                type
              }
            }
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
            "variables": {"projectId": PROJECT_UUID}
        }
    )

    if response.status_code != 200:
        return None

    data = response.json()
    if "errors" in data:
        return None

    return data.get("data", {}).get("issues", {}).get("nodes", [])


def analyze_issues(issues):
    """Analyze issues and generate report."""
    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(days=STALE_DAYS)
    
    report = {
        "total_open": len(issues),
        "by_status": {},
        "by_priority": {},
        "stale_issues": [],
        "parent_issues": [],
        "orphan_issues": [],
        "issues_needing_attention": [],
        "all_issues": []
    }
    
    for issue in issues:
        # Parse dates
        updated_at = datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))
        created_at = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
        
        # Status breakdown
        state_name = issue["state"]["name"]
        state_type = issue["state"]["type"]
        if state_name not in report["by_status"]:
            report["by_status"][state_name] = []
        report["by_status"][state_name].append(issue["identifier"])
        
        # Priority breakdown
        priority_label = issue.get("priorityLabel", "No Priority")
        if priority_label not in report["by_priority"]:
            report["by_priority"][priority_label] = []
        report["by_priority"][priority_label].append(issue["identifier"])
        
        # Check if stale
        if updated_at < stale_threshold:
            days_stale = (now - updated_at).days
            report["stale_issues"].append({
                "identifier": issue["identifier"],
                "title": issue["title"],
                "last_updated": issue["updatedAt"],
                "days_stale": days_stale,
                "status": state_name
            })
        
        # Check for parent/child relationships
        children = issue.get("children", {}).get("nodes", [])
        if children:
            child_statuses = {}
            for child in children:
                child_state = child["state"]["name"]
                if child_state not in child_statuses:
                    child_statuses[child_state] = []
                child_statuses[child_state].append(child["identifier"])
            
            report["parent_issues"].append({
                "identifier": issue["identifier"],
                "title": issue["title"],
                "status": state_name,
                "children_count": len(children),
                "children_by_status": child_statuses
            })
        
        # Check if orphan (no parent, not a parent itself)
        if not issue.get("parent") and not children:
            report["orphan_issues"].append(issue["identifier"])
        
        # Issues needing attention
        needs_attention = []
        if not issue.get("assignee"):
            needs_attention.append("No assignee")
        if not issue.get("description") or len(issue.get("description", "")) < 50:
            needs_attention.append("Missing/short description")
        if issue["priority"] == 0:
            needs_attention.append("No priority set")
        
        if needs_attention:
            report["issues_needing_attention"].append({
                "identifier": issue["identifier"],
                "title": issue["title"],
                "reasons": needs_attention
            })
        
        # Add to all issues
        report["all_issues"].append({
            "identifier": issue["identifier"],
            "title": issue["title"],
            "status": state_name,
            "status_type": state_type,
            "priority": priority_label,
            "assignee": issue.get("assignee", {}).get("name") if issue.get("assignee") else "Unassigned",
            "updated_at": issue["updatedAt"],
            "url": issue["url"],
            "parent": issue.get("parent", {}).get("identifier") if issue.get("parent") else None,
            "children_count": len(children),
            "labels": [l["name"] for l in issue.get("labels", {}).get("nodes", [])]
        })
    
    return report


def print_report(report):
    """Print formatted report."""
    print("\n" + "=" * 80)
    print("CODE-CHEF LINEAR ISSUES REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    print(f"\n📊 SUMMARY")
    print("-" * 40)
    print(f"Total Open Issues: {report['total_open']}")
    
    print(f"\n📋 BY STATUS")
    print("-" * 40)
    for status, issues in sorted(report["by_status"].items()):
        print(f"  {status}: {len(issues)} issues")
        for issue_id in issues:
            print(f"    - {issue_id}")
    
    print(f"\n🎯 BY PRIORITY")
    print("-" * 40)
    for priority, issues in sorted(report["by_priority"].items()):
        print(f"  {priority}: {len(issues)} issues")
        for issue_id in issues:
            print(f"    - {issue_id}")
    
    if report["stale_issues"]:
        print(f"\n⚠️  STALE ISSUES (no updates in {STALE_DAYS}+ days)")
        print("-" * 40)
        for issue in report["stale_issues"]:
            print(f"  {issue['identifier']}: {issue['title'][:50]}...")
            print(f"    Last updated: {issue['days_stale']} days ago | Status: {issue['status']}")
    else:
        print(f"\n✅ No stale issues (all updated within {STALE_DAYS} days)")
    
    if report["parent_issues"]:
        print(f"\n👪 PARENT ISSUES WITH SUB-ISSUES")
        print("-" * 40)
        for parent in report["parent_issues"]:
            print(f"  {parent['identifier']}: {parent['title'][:40]}...")
            print(f"    Status: {parent['status']} | {parent['children_count']} sub-issues")
            for status, children in parent["children_by_status"].items():
                print(f"      {status}: {', '.join(children)}")
    
    if report["issues_needing_attention"]:
        print(f"\n🔍 ISSUES NEEDING ATTENTION")
        print("-" * 40)
        for issue in report["issues_needing_attention"]:
            print(f"  {issue['identifier']}: {issue['title'][:40]}...")
            for reason in issue["reasons"]:
                print(f"    ⚠️  {reason}")
    
    print(f"\n📝 ALL OPEN ISSUES (Detailed)")
    print("-" * 40)
    for issue in report["all_issues"]:
        print(f"\n  {issue['identifier']}: {issue['title']}")
        print(f"    Status: {issue['status']} ({issue['status_type']})")
        print(f"    Priority: {issue['priority']}")
        print(f"    Assignee: {issue['assignee']}")
        print(f"    Updated: {issue['updated_at']}")
        if issue['parent']:
            print(f"    Parent: {issue['parent']}")
        if issue['children_count'] > 0:
            print(f"    Sub-issues: {issue['children_count']}")
        if issue['labels']:
            print(f"    Labels: {', '.join(issue['labels'])}")
        print(f"    URL: {issue['url']}")
    
    print("\n" + "=" * 80)
    print("END OF REPORT")
    print("=" * 80)


def main():
    print("Fetching open issues from Linear...")
    issues = fetch_open_issues()
    
    if issues is None:
        print("Failed to fetch issues")
        return
    
    if not issues:
        print("No open issues found")
        return
    
    print(f"Found {len(issues)} open issues")
    
    report = analyze_issues(issues)
    print_report(report)
    
    # Also output as JSON for further processing
    json_report_path = "support/reports/linear-open-issues-report.json"
    with open(json_report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 JSON report saved to: {json_report_path}")


if __name__ == "__main__":
    main()

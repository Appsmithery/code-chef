#!/usr/bin/env python3
"""
Index Issue Tracker to Qdrant
Syncs Linear issues to issue_tracker collection.
Useful for agents to understand current tasks, bugs, and feature requests.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import httpx

# Add repo root to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Configuration
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8007")
COLLECTION_NAME = "issue_tracker"
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY") or os.getenv("LINEAR_OAUTH_DEV_TOKEN")
LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID", "f5b610be-ac34-4983-918b-2c9d00aa9b7a")

ISSUES_QUERY = """
query GetIssues($teamId: String!) {
  team(id: $teamId) {
    issues(first: 200, orderBy: updatedAt) {
      nodes {
        id
        identifier
        title
        description
        priority
        estimate
        createdAt
        updatedAt
        completedAt
        canceledAt
        state {
          id
          name
          type
        }
        assignee {
          id
          name
          email
        }
        creator {
          id
          name
        }
        project {
          id
          name
        }
        parent {
          id
          identifier
          title
        }
        labels {
          nodes {
            id
            name
            color
          }
        }
        comments {
          nodes {
            id
            body
            createdAt
            user {
              name
            }
          }
        }
        url
      }
    }
  }
}
"""


async def fetch_linear_issues() -> List[Dict[str, Any]]:
    """Fetch all issues from Linear via GraphQL API"""
    if not LINEAR_API_KEY:
        print("❌ LINEAR_API_KEY not found in environment")
        sys.exit(1)

    print(f"📡 Fetching issues from Linear (Team: {LINEAR_TEAM_ID})...")

    headers = {
        "Authorization": LINEAR_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {"query": ISSUES_QUERY, "variables": {"teamId": LINEAR_TEAM_ID}}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(LINEAR_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                return []

            issues = (
                data.get("data", {}).get("team", {}).get("issues", {}).get("nodes", [])
            )
            print(f"✅ Fetched {len(issues)} issues")
            return issues

    except httpx.HTTPError as e:
        print(f"❌ HTTP error fetching issues: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching issues: {e}")
        return []


def issue_to_document(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Linear issue to searchable document"""
    issue_id = issue.get("id", "")
    identifier = issue.get("identifier", "")
    title = issue.get("title", "Untitled Issue")
    description = issue.get("description", "")
    priority = issue.get("priority", 0)
    estimate = issue.get("estimate", None)
    url = issue.get("url", "")

    # State information
    state = issue.get("state", {})
    state_name = state.get("name", "unknown")
    state_type = state.get("type", "unknown")

    # People
    assignee = issue.get("assignee", {})
    assignee_name = assignee.get("name", "Unassigned") if assignee else "Unassigned"

    creator = issue.get("creator", {})
    creator_name = creator.get("name", "Unknown") if creator else "Unknown"

    # Project
    project = issue.get("project", {})
    project_name = project.get("name", "No Project") if project else "No Project"

    # Parent issue (if sub-issue)
    parent = issue.get("parent", {})
    parent_identifier = parent.get("identifier", "") if parent else ""
    parent_title = parent.get("title", "") if parent else ""

    # Labels
    labels = issue.get("labels", {}).get("nodes", [])
    label_names = [l.get("name", "") for l in labels if l.get("name")]

    # Comments (extract key discussion points)
    comments = issue.get("comments", {}).get("nodes", [])
    comment_count = len(comments)
    recent_comments = comments[-3:] if comments else []  # Last 3 comments

    # Priority mapping
    priority_map = {0: "No Priority", 1: "Urgent", 2: "High", 3: "Normal", 4: "Low"}
    priority_label = priority_map.get(priority, "Unknown")

    # Build searchable content
    content_parts = [
        f"# {identifier}: {title}",
        f"**Status**: {state_name} ({state_type})",
        f"**Priority**: {priority_label}",
        f"**Assignee**: {assignee_name}",
        f"**Project**: {project_name}",
    ]

    if estimate:
        content_parts.append(f"**Estimate**: {estimate} points")

    if parent_identifier:
        content_parts.append(f"**Parent Issue**: {parent_identifier} - {parent_title}")

    if description:
        content_parts.append(f"\n## Description\n{description}")

    if label_names:
        content_parts.append(f"\n## Labels\n{', '.join(label_names)}")

    if recent_comments:
        content_parts.append("\n## Recent Discussion")
        for comment in recent_comments:
            if comment is None:
                continue
            user_obj = comment.get("user") or {}
            user = user_obj.get("name", "Unknown") if user_obj else "Unknown"
            body = (comment.get("body") or "")[:200]  # First 200 chars
            content_parts.append(f"- **{user}**: {body}...")

    content_parts.append(f"\n**Linear URL**: {url}")

    # Determine if completed or active
    is_completed = bool(issue.get("completedAt"))
    is_canceled = bool(issue.get("canceledAt"))

    return {
        "content": "\n".join(content_parts),
        "issue_id": issue_id,
        "identifier": identifier,
        "title": title,
        "state_name": state_name,
        "state_type": state_type,
        "priority": priority,
        "priority_label": priority_label,
        "estimate": estimate,
        "assignee": assignee_name,
        "creator": creator_name,
        "project_name": project_name,
        "parent_identifier": parent_identifier,
        "labels": label_names,
        "comment_count": comment_count,
        "url": url,
        "is_completed": is_completed,
        "is_canceled": is_canceled,
        "is_active": not is_completed and not is_canceled,
        "created_at": issue.get("createdAt", ""),
        "updated_at": issue.get("updatedAt", ""),
        "completed_at": issue.get("completedAt", ""),
    }


async def index_to_rag_service(documents: List[Dict[str, Any]]):
    """Index issues to RAG service"""
    if not documents:
        print("No documents to index")
        return

    print(f"\n📤 Indexing {len(documents)} issues to RAG service...")

    # Prepare documents and metadata
    doc_contents = [d["content"] for d in documents]
    metadatas = [
        {
            "issue_id": d["issue_id"],
            "identifier": d["identifier"],
            "title": d["title"],
            "state_name": d["state_name"],
            "state_type": d["state_type"],
            "priority": d["priority"],
            "priority_label": d["priority_label"],
            "estimate": d["estimate"],
            "assignee": d["assignee"],
            "project_name": d["project_name"],
            "labels": d["labels"][:10],  # Limit to 10 labels
            "comment_count": d["comment_count"],
            "url": d["url"],
            "is_active": d["is_active"],
            "is_completed": d["is_completed"],
            "updated_at": d["updated_at"],
            "indexed_at": datetime.utcnow().isoformat(),
        }
        for d in documents
    ]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/index",
                json={
                    "documents": doc_contents,
                    "metadatas": metadatas,
                    "collection": COLLECTION_NAME,
                },
            )
            response.raise_for_status()
            result = response.json()

            print(f"✅ Successfully indexed {result['indexed_count']} issues")
            print(f"   Collection: {result['collection']}")
            return result

    except httpx.HTTPError as e:
        print(f"❌ HTTP error during indexing: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")
        raise
    except Exception as e:
        print(f"❌ Error indexing issues: {e}")
        raise


async def main():
    """Main indexing workflow"""
    print("=" * 70)
    print("🎫 Issue Tracker Indexing - Linear Issue Sync")
    print("=" * 70)

    # Fetch issues from Linear
    issues = await fetch_linear_issues()

    if not issues:
        print("⚠️ No issues found or error occurred")
        return

    # Convert to searchable documents
    print("\n🔄 Converting issues to searchable documents...")
    documents = []

    for issue in issues:
        doc = issue_to_document(issue)
        documents.append(doc)
        status_icon = (
            "✅" if doc["is_completed"] else "🔄" if doc["is_active"] else "❌"
        )
        print(f"  {status_icon} {doc['identifier']}: {doc['title'][:60]}...")

    print(f"\n✅ Prepared {len(documents)} issue documents")

    # Show statistics
    state_type_counts = {}
    priority_counts = {}
    for doc in documents:
        state_type = doc["state_type"]
        priority = doc["priority_label"]
        state_type_counts[state_type] = state_type_counts.get(state_type, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    print("\n📊 Issue Statistics:")
    print("  State Types:")
    for state, count in sorted(state_type_counts.items()):
        print(f"    {state}: {count}")

    print("  Priority Distribution:")
    for priority, count in sorted(priority_counts.items()):
        print(f"    {priority}: {count}")

    # Index to RAG service
    if documents:
        await index_to_rag_service(documents)

    print("\n" + "=" * 70)
    print("✅ Issue Tracker Indexing Complete!")
    print("=" * 70)
    print(f"\n💡 Query examples:")
    print(f"   curl -X POST {RAG_SERVICE_URL}/query \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(
        f'     -d \'{{"query": "high priority authentication bugs", "collection": "{COLLECTION_NAME}"}}\''
    )


if __name__ == "__main__":
    asyncio.run(main())

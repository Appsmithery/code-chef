#!/usr/bin/env python3
"""
Index Feature Specs to Qdrant
Syncs Linear project descriptions and requirements to feature_specs collection.
Useful for agents to understand project context and requirements.
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
COLLECTION_NAME = "feature_specs"
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY") or os.getenv("LINEAR_OAUTH_DEV_TOKEN")
LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_TEAM_ID = os.getenv(
    "LINEAR_TEAM_ID", "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
)  # Project Roadmaps team


PROJECTS_QUERY = """
query GetProjects {
  projects(first: 50) {
    nodes {
      id
      name
      description
      state
      priority
      startDate
      targetDate
      completedAt
      createdAt
      updatedAt
      lead {
        id
        name
        email
      }
      url
    }
  }
}
"""


async def fetch_linear_projects() -> List[Dict[str, Any]]:
    """Fetch all projects from Linear via GraphQL API"""
    if not LINEAR_API_KEY:
        print("❌ LINEAR_API_KEY not found in environment")
        sys.exit(1)

    print(f"📡 Fetching projects from Linear...")

    headers = {
        "Authorization": LINEAR_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {"query": PROJECTS_QUERY}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(LINEAR_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                return []

            projects = data.get("data", {}).get("projects", {}).get("nodes", [])
            print(f"✅ Fetched {len(projects)} projects")
            return projects

    except httpx.HTTPError as e:
        print(f"❌ HTTP error fetching projects: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching projects: {e}")
        return []


def project_to_document(project: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Linear project to searchable document"""
    project_id = project.get("id", "")
    name = project.get("name", "Untitled Project")
    description = project.get("description", "")
    state = project.get("state", "unknown")
    priority = project.get("priority", 0)
    url = project.get("url", "")

    # Extract lead information
    lead = project.get("lead") or {}
    lead_name = lead.get("name", "Unassigned") if lead else "Unassigned"

    # Build searchable content
    content_parts = [
        f"# {name}",
        f"**Status**: {state}",
        f"**Priority**: {priority}",
        f"**Lead**: {lead_name}",
    ]

    if description:
        content_parts.append(f"\n## Description\n{description}")

    # Add dates if available
    start_date = project.get("startDate")
    target_date = project.get("targetDate")
    if start_date or target_date:
        content_parts.append(f"\n## Timeline")
        if start_date:
            content_parts.append(f"- Start: {start_date}")
        if target_date:
            content_parts.append(f"- Target: {target_date}")

    content_parts.append(f"\n**Linear URL**: {url}")

    return {
        "content": "\n".join(content_parts),
        "project_id": project_id,
        "project_name": name,
        "state": state,
        "priority": priority,
        "lead": lead_name,
        "url": url,
        "created_at": project.get("createdAt", ""),
        "updated_at": project.get("updatedAt", ""),
        "start_date": project.get("startDate", ""),
        "target_date": project.get("targetDate", ""),
        "completed_at": project.get("completedAt", ""),
    }


async def index_to_rag_service(documents: List[Dict[str, Any]]):
    """Index feature specs to RAG service"""
    if not documents:
        print("No documents to index")
        return

    print(f"\n📤 Indexing {len(documents)} feature specs to RAG service...")

    # Prepare documents and metadata
    doc_contents = [d["content"] for d in documents]
    metadatas = [
        {
            "project_id": d["project_id"],
            "project_name": d["project_name"],
            "state": d["state"],
            "priority": d["priority"],
            "lead": d["lead"],
            "url": d["url"],
            "start_date": d.get("start_date", ""),
            "target_date": d.get("target_date", ""),
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

            print(f"✅ Successfully indexed {result['indexed_count']} feature specs")
            print(f"   Collection: {result['collection']}")
            return result

    except httpx.HTTPError as e:
        print(f"❌ HTTP error during indexing: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")
        raise
    except Exception as e:
        print(f"❌ Error indexing feature specs: {e}")
        raise


async def main():
    """Main indexing workflow"""
    print("=" * 70)
    print("📋 Feature Specs Indexing - Linear Project Sync")
    print("=" * 70)

    # Fetch projects from Linear
    projects = await fetch_linear_projects()

    if not projects:
        print("⚠️ No projects found or error occurred")
        return

    # Convert to searchable documents
    print("\n🔄 Converting projects to searchable documents...")
    documents = []

    for project in projects:
        doc = project_to_document(project)
        documents.append(doc)
        print(f"  ✓ {doc['project_name']} ({doc['state']})")

    print(f"\n✅ Prepared {len(documents)} feature spec documents")

    # Show state distribution
    state_counts = {}
    for doc in documents:
        state = doc["state"]
        state_counts[state] = state_counts.get(state, 0) + 1

    print("\n📊 Project State Distribution:")
    for state, count in sorted(state_counts.items()):
        print(f"   {state}: {count}")

    # Index to RAG service
    if documents:
        await index_to_rag_service(documents)

    print("\n" + "=" * 70)
    print("✅ Feature Specs Indexing Complete!")
    print("=" * 70)
    print(f"\n💡 Query examples:")
    print(f"   curl -X POST {RAG_SERVICE_URL}/query \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(
        f'     -d \'{{"query": "authentication features in progress", "collection": "{COLLECTION_NAME}"}}\''
    )


if __name__ == "__main__":
    asyncio.run(main())

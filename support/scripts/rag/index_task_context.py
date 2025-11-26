#!/usr/bin/env python3
"""
Index Task Context to Qdrant
Syncs workflow events and execution history to task_context collection.
Useful for agents to learn from past executions and avoid repeating mistakes.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# Add repo root to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Configuration
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8007")
COLLECTION_NAME = "task_context"

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "devtools")
DB_USER = os.getenv("DB_USER", "devtools")
DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")


def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor,
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None


async def fetch_workflow_executions() -> List[Dict[str, Any]]:
    """Fetch workflow executions from workflow_events table"""
    conn = get_db_connection()
    if not conn:
        return []

    print(f"📡 Fetching workflow executions from database...")

    try:
        cursor = conn.cursor()

        # Query to get workflow summaries with aggregated events
        query = """
        WITH workflow_summary AS (
            SELECT 
                workflow_id,
                MIN(timestamp) as start_time,
                MAX(timestamp) as end_time,
                COUNT(*) as event_count,
                jsonb_agg(
                    jsonb_build_object(
                        'action', action,
                        'step_id', step_id,
                        'timestamp', timestamp,
                        'data', data
                    ) ORDER BY timestamp
                ) as events
            FROM workflow_events
            GROUP BY workflow_id
        ),
        workflow_meta AS (
            SELECT 
                workflow_id,
                template_name,
                status,
                started_at,
                completed_at,
                total_events,
                steps_completed,
                steps_failed
            FROM workflow_metadata
        )
        SELECT 
            ws.workflow_id,
            ws.start_time,
            ws.end_time,
            ws.event_count,
            ws.events,
            wm.template_name,
            wm.status,
            wm.steps_completed,
            wm.steps_failed,
            EXTRACT(EPOCH FROM (ws.end_time - ws.start_time)) as duration_seconds
        FROM workflow_summary ws
        LEFT JOIN workflow_meta wm ON ws.workflow_id = wm.workflow_id
        ORDER BY ws.start_time DESC
        LIMIT 100;
        """

        cursor.execute(query)
        workflows = cursor.fetchall()

        print(f"✅ Fetched {len(workflows)} workflow executions")

        cursor.close()
        conn.close()

        return workflows

    except Exception as e:
        print(f"❌ Error fetching workflows: {e}")
        if conn:
            conn.close()
        return []


def workflow_to_document(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Convert workflow execution to searchable document"""
    workflow_id = workflow.get("workflow_id", "")
    template_name = workflow.get("template_name", "Unknown Template")
    status = workflow.get("status", "unknown")
    start_time = workflow.get("start_time", "")
    end_time = workflow.get("end_time", "")
    duration_seconds = workflow.get("duration_seconds", 0)
    event_count = workflow.get("event_count", 0)
    steps_completed = workflow.get("steps_completed", 0)
    steps_failed = workflow.get("steps_failed", 0)

    # Parse events
    events = workflow.get("events", [])

    # Extract key actions
    actions = [e.get("action") for e in events if e.get("action")]
    action_counts = {}
    for action in actions:
        action_counts[action] = action_counts.get(action, 0) + 1

    # Extract participating agents from step_ids or data
    agents = set()
    steps = set()
    for event in events:
        step_id = event.get("step_id", "")
        if step_id:
            steps.add(step_id)

        data = event.get("data", {})
        if isinstance(data, dict):
            # Extract agents from various data fields
            if "participating_agents" in data:
                for agent in data["participating_agents"]:
                    if agent:
                        agents.add(agent)
            if "agent" in data:
                agents.add(data["agent"])

    # Determine outcome
    is_successful = status in ["completed", "done"]
    is_failed = status in ["failed", "error"]
    is_paused = status in ["paused", "waiting", "approval_pending"]

    # Build searchable content
    content_parts = [
        f"# Workflow Execution: {template_name}",
        f"**Workflow ID**: {workflow_id}",
        f"**Status**: {status}",
        f"**Duration**: {int(duration_seconds)} seconds",
        f"**Events**: {event_count}",
    ]

    if steps_completed > 0 or steps_failed > 0:
        content_parts.append(f"**Steps Completed**: {steps_completed}")
        content_parts.append(f"**Steps Failed**: {steps_failed}")

    if agents:
        content_parts.append(f"\n## Participating Agents\n{', '.join(sorted(agents))}")

    if steps:
        content_parts.append(f"\n## Workflow Steps\n{', '.join(sorted(steps))}")

    if action_counts:
        content_parts.append("\n## Action Summary")
        for action, count in sorted(
            action_counts.items(), key=lambda x: x[1], reverse=True
        ):
            content_parts.append(f"- {action}: {count}")

    # Add outcome classification
    if is_successful:
        content_parts.append("\n✅ **Outcome**: Successfully completed")
    elif is_failed:
        content_parts.append("\n❌ **Outcome**: Failed")
        # Try to extract error information
        error_events = [
            e
            for e in events
            if e.get("action") in ["fail_step", "rollback_step", "cancel_workflow"]
        ]
        if error_events:
            content_parts.append("\n### Failure Details")
            for e in error_events[:3]:  # Show first 3 errors
                error_data = e.get("data", {})
                if isinstance(error_data, dict) and "error" in error_data:
                    content_parts.append(
                        f"- {error_data.get('error', 'Unknown error')}"
                    )
    elif is_paused:
        content_parts.append("\n⏸️ **Outcome**: Paused (awaiting approval/input)")

    # Add timeline summary (first and last few events)
    if events:
        content_parts.append("\n## Timeline")
        timeline_events = events[:3] + (events[-3:] if len(events) > 6 else [])
        seen = set()
        for event in timeline_events:
            event_str = f"{event.get('timestamp', '')}: {event.get('action', '')} - {event.get('step_id', '')}"
            if event_str not in seen:
                content_parts.append(f"- {event_str}")
                seen.add(event_str)

    content_parts.append(f"\n**Execution Period**: {start_time} to {end_time}")

    return {
        "content": "\n".join(content_parts),
        "workflow_id": workflow_id,
        "template_name": template_name,
        "status": status,
        "is_successful": is_successful,
        "is_failed": is_failed,
        "duration_seconds": int(duration_seconds) if duration_seconds else 0,
        "event_count": event_count,
        "steps_completed": steps_completed,
        "steps_failed": steps_failed,
        "participating_agents": list(agents),
        "workflow_steps": list(steps),
        "action_types": list(action_counts.keys()),
        "start_time": str(start_time) if start_time else "",
        "end_time": str(end_time) if end_time else "",
    }


async def index_to_rag_service(documents: List[Dict[str, Any]]):
    """Index task context to RAG service"""
    if not documents:
        print("No documents to index")
        return

    print(f"\n📤 Indexing {len(documents)} workflow executions to RAG service...")

    # Prepare documents and metadata
    doc_contents = [d["content"] for d in documents]
    metadatas = [
        {
            "workflow_id": d["workflow_id"],
            "template_name": d["template_name"],
            "status": d["status"],
            "is_successful": d["is_successful"],
            "is_failed": d["is_failed"],
            "duration_seconds": d["duration_seconds"],
            "event_count": d["event_count"],
            "steps_completed": d["steps_completed"],
            "steps_failed": d["steps_failed"],
            "participating_agents": d["participating_agents"][:10],  # Limit to 10
            "workflow_steps": d["workflow_steps"][:20],  # Limit to 20
            "action_types": d["action_types"][:15],  # Limit to 15
            "start_time": d["start_time"],
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

            print(
                f"✅ Successfully indexed {result['indexed_count']} workflow executions"
            )
            print(f"   Collection: {result['collection']}")
            return result

    except httpx.HTTPError as e:
        print(f"❌ HTTP error during indexing: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")
        raise
    except Exception as e:
        print(f"❌ Error indexing task context: {e}")
        raise


async def main():
    """Main indexing workflow"""
    print("=" * 70)
    print("📊 Task Context Indexing - Workflow History Sync")
    print("=" * 70)

    # Fetch workflow executions from database
    workflows = await fetch_workflow_executions()

    if not workflows:
        print("⚠️ No workflows found or error occurred")
        print(
            "   This is expected if event sourcing was just deployed (0 workflow events)"
        )
        return

    # Convert to searchable documents
    print("\n🔄 Converting workflows to searchable documents...")
    documents = []

    for workflow in workflows:
        doc = workflow_to_document(workflow)
        documents.append(doc)
        status_icon = (
            "✅" if doc["is_successful"] else "❌" if doc["is_failed"] else "⏸️"
        )
        print(
            f"  {status_icon} {doc['template_name']}: {doc['duration_seconds']}s, {doc['event_count']} events"
        )

    print(f"\n✅ Prepared {len(documents)} workflow documents")

    # Show statistics
    status_counts = {}
    template_counts = {}
    for doc in documents:
        status = doc["status"]
        template = doc["template_name"]
        status_counts[status] = status_counts.get(status, 0) + 1
        template_counts[template] = template_counts.get(template, 0) + 1

    print("\n📊 Workflow Statistics:")
    print("  Status Distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"    {status}: {count}")

    print("  Template Distribution:")
    for template, count in sorted(template_counts.items()):
        print(f"    {template}: {count}")

    # Index to RAG service
    if documents:
        await index_to_rag_service(documents)

    print("\n" + "=" * 70)
    print("✅ Task Context Indexing Complete!")
    print("=" * 70)
    print(f"\n💡 Query examples:")
    print(f"   curl -X POST {RAG_SERVICE_URL}/query \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(
        f'     -d \'{{"query": "successful deployment workflows with feature_dev agent", "collection": "{COLLECTION_NAME}"}}\''
    )


if __name__ == "__main__":
    asyncio.run(main())

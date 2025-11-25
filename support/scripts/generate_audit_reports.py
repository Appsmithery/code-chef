#!/usr/bin/env python3
"""
Automated Audit Report Generation Script

This script generates PDF audit reports for completed workflows on a scheduled basis.
Intended to run as a cron job weekly for compliance documentation.

Usage:
    # Generate reports for all workflows completed in last 7 days
    python generate_audit_reports.py

    # Generate reports for specific time range
    python generate_audit_reports.py --days 30

    # Generate report for specific workflow
    python generate_audit_reports.py --workflow-id abc-123

Schedule as cron job:
    # Run every Sunday at 2 AM
    0 2 * * 0 /usr/bin/python3 /opt/Dev-Tools/support/scripts/generate_audit_reports.py
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add project paths
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "shared"))

import asyncpg
from shared.lib.workflow_events import export_events_to_pdf


async def get_completed_workflows(
    pool: asyncpg.Pool, days_back: int = 7
) -> List[Dict[str, Any]]:
    """Query PostgreSQL for completed workflows

    Args:
        pool: asyncpg connection pool
        days_back: Number of days to look back

    Returns:
        List of workflow metadata dictionaries
    """

    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    query = """
        SELECT 
            workflow_id,
            template_name,
            status,
            created_at,
            updated_at,
            total_events,
            steps_completed
        FROM workflow_metadata
        WHERE status IN ('completed', 'failed', 'cancelled')
          AND updated_at >= $1
        ORDER BY updated_at DESC
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, cutoff_date)

    return [dict(row) for row in rows]


async def get_workflow_events(
    pool: asyncpg.Pool, workflow_id: str
) -> List[Dict[str, Any]]:
    """Load all events for a workflow

    Args:
        pool: asyncpg connection pool
        workflow_id: Workflow identifier

    Returns:
        List of event dictionaries
    """

    query = """
        SELECT 
            event_id,
            workflow_id,
            action,
            step_id,
            data,
            timestamp,
            event_version,
            signature
        FROM workflow_events
        WHERE workflow_id = $1
        ORDER BY timestamp ASC
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, workflow_id)

    # Convert to dictionaries
    events = []
    for row in rows:
        event_dict = dict(row)
        # Convert timestamp to ISO string
        if isinstance(event_dict["timestamp"], datetime):
            event_dict["timestamp"] = event_dict["timestamp"].isoformat() + "Z"
        events.append(event_dict)

    return events


async def generate_report_for_workflow(
    pool: asyncpg.Pool, workflow_id: str, output_dir: Path
) -> Path:
    """Generate audit report for a single workflow

    Args:
        pool: asyncpg connection pool
        workflow_id: Workflow identifier
        output_dir: Directory to save report

    Returns:
        Path to generated PDF file
    """

    print(f"Generating report for workflow: {workflow_id}")

    # Load workflow metadata
    query_metadata = """
        SELECT 
            workflow_id,
            template_name,
            status,
            created_at,
            updated_at,
            total_events,
            steps_completed
        FROM workflow_metadata
        WHERE workflow_id = $1
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query_metadata, workflow_id)

    if not row:
        print(f"  ⚠️  Workflow not found: {workflow_id}")
        return None

    metadata = dict(row)

    # Convert timestamps to strings
    if isinstance(metadata.get("created_at"), datetime):
        metadata["created_at"] = metadata["created_at"].isoformat() + "Z"
    if isinstance(metadata.get("updated_at"), datetime):
        metadata["updated_at"] = metadata["updated_at"].isoformat() + "Z"

    # Load events
    events = await get_workflow_events(pool, workflow_id)

    if not events:
        print(f"  ⚠️  No events found for workflow: {workflow_id}")
        return None

    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    template_name = metadata.get("template_name", "unknown").replace("/", "_")
    filename = f"audit_report_{template_name}_{workflow_id[:8]}_{timestamp}.pdf"
    output_path = output_dir / filename

    # Generate PDF
    try:
        export_events_to_pdf(
            workflow_id=workflow_id,
            events=events,
            metadata=metadata,
            output_path=str(output_path),
        )

        print(f"  ✅ Report generated: {output_path}")
        return output_path

    except Exception as e:
        print(f"  ❌ Error generating report: {e}")
        return None


async def archive_old_events(pool: asyncpg.Pool, retention_days: int = 90):
    """Archive events older than retention period

    Calls the PostgreSQL function archive_old_events() which moves
    events to workflow_events_archive table.

    Args:
        pool: asyncpg connection pool
        retention_days: Days to retain in main table
    """

    print(f"\nArchiving events older than {retention_days} days...")

    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT archive_old_events($1)", retention_days)

    print(f"  ✅ Archived {result} events")


async def compress_archived_events(pool: asyncpg.Pool, output_dir: Path):
    """Export archived events to gzip-compressed JSON files

    This reduces storage requirements for long-term event retention.

    Args:
        pool: asyncpg connection pool
        output_dir: Directory to save compressed archives
    """

    print("\nCompressing archived events...")

    query = """
        SELECT 
            event_id,
            workflow_id,
            action,
            step_id,
            data,
            timestamp,
            event_version,
            signature,
            archived_at
        FROM workflow_events_archive
        WHERE archived_at > NOW() - INTERVAL '7 days'
        ORDER BY archived_at DESC
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query)

    if not rows:
        print("  ℹ️  No recently archived events to compress")
        return

    # Group by workflow
    workflows = {}
    for row in rows:
        workflow_id = row["workflow_id"]
        if workflow_id not in workflows:
            workflows[workflow_id] = []

        event_dict = dict(row)
        if isinstance(event_dict["timestamp"], datetime):
            event_dict["timestamp"] = event_dict["timestamp"].isoformat() + "Z"
        if isinstance(event_dict["archived_at"], datetime):
            event_dict["archived_at"] = event_dict["archived_at"].isoformat() + "Z"

        workflows[workflow_id].append(event_dict)

    # Compress each workflow's events
    import gzip
    import json

    for workflow_id, events in workflows.items():
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        filename = f"archived_events_{workflow_id[:8]}_{timestamp}.json.gz"
        output_path = output_dir / filename

        with gzip.open(output_path, "wt", encoding="utf-8") as f:
            json.dump(events, f, indent=2, default=str)

        print(f"  ✅ Compressed {len(events)} events: {output_path}")


async def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Generate audit reports for completed workflows"
    )
    parser.add_argument(
        "--days", type=int, default=7, help="Number of days to look back (default: 7)"
    )
    parser.add_argument(
        "--workflow-id", type=str, help="Generate report for specific workflow ID"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/var/log/workflow-audits"),
        help="Output directory for reports (default: /var/log/workflow-audits)",
    )
    parser.add_argument(
        "--archive", action="store_true", help="Archive old events (90+ days)"
    )
    parser.add_argument(
        "--compress", action="store_true", help="Compress archived events to gzip"
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Get database URL from environment
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devtools"
    )

    print(f"📊 Workflow Audit Report Generation")
    print(f"{'=' * 60}")
    print(f"Output directory: {args.output_dir}")
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print()

    # Connect to database
    try:
        pool = await asyncpg.create_pool(db_url, min_size=2, max_size=5)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1

    try:
        if args.workflow_id:
            # Generate report for specific workflow
            output_path = await generate_report_for_workflow(
                pool, args.workflow_id, args.output_dir
            )

            if output_path:
                print(f"\n✅ Report generated successfully: {output_path}")
                return 0
            else:
                return 1

        else:
            # Generate reports for all completed workflows
            workflows = await get_completed_workflows(pool, args.days)

            print(
                f"Found {len(workflows)} completed workflows in last {args.days} days\n"
            )

            success_count = 0
            for workflow_meta in workflows:
                workflow_id = workflow_meta["workflow_id"]
                output_path = await generate_report_for_workflow(
                    pool, workflow_id, args.output_dir
                )

                if output_path:
                    success_count += 1

            print(f"\n{'=' * 60}")
            print(f"✅ Generated {success_count}/{len(workflows)} audit reports")

        # Archive old events if requested
        if args.archive:
            await archive_old_events(pool, retention_days=90)

        # Compress archived events if requested
        if args.compress:
            await compress_archived_events(pool, args.output_dir)

        return 0

    finally:
        await pool.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

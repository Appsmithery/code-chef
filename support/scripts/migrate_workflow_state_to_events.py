#!/usr/bin/env python3
"""
Migration Script: Workflow State → Event Sourcing

This script migrates existing workflow state from the old workflow_state table
to the new event-sourced architecture using workflow_events.

Strategy:
1. Backfill events for existing workflows
2. Convert mutation-based state to immutable event log
3. Validate migrated workflows with replay
4. Generate synthetic events for missing transitions

Usage:
    # Dry run (no changes)
    python migrate_workflow_state_to_events.py --dry-run

    # Migrate specific workflow
    python migrate_workflow_state_to_events.py --workflow-id abc-123

    # Migrate all workflows
    python migrate_workflow_state_to_events.py --all

    # Validate migrations only
    python migrate_workflow_state_to_events.py --validate-only
"""

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project paths
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "shared"))

import asyncpg
from shared.lib.workflow_reducer import (
    WorkflowAction,
    WorkflowEvent,
    replay_workflow,
)
from shared.lib.workflow_events import sign_event, serialize_event


async def get_legacy_workflows(pool: asyncpg.Pool) -> List[Dict[str, Any]]:
    """Query old workflow_state table for workflows needing migration

    Args:
        pool: asyncpg connection pool

    Returns:
        List of legacy workflow states
    """

    # This assumes a legacy workflow_state table exists
    query = """
        SELECT 
            id as workflow_id,
            template_name,
            status,
            current_step,
            steps_completed,
            outputs,
            approvals,
            error,
            created_at,
            updated_at
        FROM workflow_state
        WHERE NOT EXISTS (
            SELECT 1 FROM workflow_metadata wm
            WHERE wm.workflow_id = workflow_state.id
        )
        ORDER BY created_at DESC
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

        return [dict(row) for row in rows]

    except asyncpg.UndefinedTableError:
        # Table doesn't exist yet - no migration needed
        print("⚠️  Legacy workflow_state table not found - no migration needed")
        return []


async def backfill_events_for_workflow(
    pool: asyncpg.Pool, legacy_state: Dict[str, Any], secret_key: str
) -> List[WorkflowEvent]:
    """Generate synthetic events from legacy state

    Creates a plausible event sequence from the final state.

    Args:
        pool: asyncpg connection pool
        legacy_state: Legacy workflow state dictionary
        secret_key: Secret key for event signatures

    Returns:
        List of synthetic WorkflowEvent objects
    """

    workflow_id = legacy_state["workflow_id"]
    events = []

    # Generate timestamp sequence
    created_at = legacy_state.get("created_at", datetime.utcnow())
    updated_at = legacy_state.get("updated_at", datetime.utcnow())

    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

    # Calculate time delta between events
    total_duration = (updated_at - created_at).total_seconds()
    steps_completed = legacy_state.get("steps_completed", [])
    num_events = len(steps_completed) + 1  # +1 for START_WORKFLOW

    time_per_event = timedelta(seconds=total_duration / max(num_events, 1))

    # 1. START_WORKFLOW event
    start_timestamp = created_at
    start_event = WorkflowEvent(
        event_id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id=steps_completed[0] if steps_completed else "init",
        data={
            "context": {},
            "template_name": legacy_state.get("template_name", "unknown"),
            "migrated": True,
            "original_created_at": created_at.isoformat(),
        },
        timestamp=start_timestamp.isoformat() + "Z",
        event_version=2,
        signature=None,
    )
    events.append(start_event)

    # 2. COMPLETE_STEP events for each completed step
    current_timestamp = start_timestamp
    outputs = legacy_state.get("outputs", {})

    for i, step_id in enumerate(steps_completed):
        current_timestamp += time_per_event

        complete_event = WorkflowEvent(
            event_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id=step_id,
            data={
                "result": outputs.get(step_id, {"status": "success"}),
                "migrated": True,
            },
            timestamp=current_timestamp.isoformat() + "Z",
            event_version=2,
            signature=None,
        )
        events.append(complete_event)

    # 3. Approval events if present
    approvals = legacy_state.get("approvals", {})
    if approvals:
        for gate_id, approval_data in approvals.items():
            current_timestamp += timedelta(seconds=60)

            approve_event = WorkflowEvent(
                event_id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                action=WorkflowAction.APPROVE_GATE,
                step_id=gate_id,
                data={
                    "approver": approval_data.get("approver", "system"),
                    "approver_role": approval_data.get("approver_role", "unknown"),
                    "comment": approval_data.get("comment", "Migrated approval"),
                    "migrated": True,
                },
                timestamp=current_timestamp.isoformat() + "Z",
                event_version=2,
                signature=None,
            )
            events.append(approve_event)

    # 4. Final status event (if failed or cancelled)
    status = legacy_state.get("status", "completed")

    if status == "failed":
        error = legacy_state.get("error", {})

        fail_event = WorkflowEvent(
            event_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            action=WorkflowAction.FAIL_STEP,
            step_id=legacy_state.get("current_step", "unknown"),
            data={
                "error": error.get("message", "Unknown error"),
                "error_type": error.get("type", "unknown"),
                "migrated": True,
            },
            timestamp=updated_at.isoformat() + "Z",
            event_version=2,
            signature=None,
        )
        events.append(fail_event)

    elif status == "cancelled":
        cancel_event = WorkflowEvent(
            event_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            action=WorkflowAction.CANCEL_WORKFLOW,
            step_id=legacy_state.get("current_step", "unknown"),
            data={
                "reason": "Migrated cancelled workflow",
                "cancelled_by": "system",
                "migrated": True,
            },
            timestamp=updated_at.isoformat() + "Z",
            event_version=2,
            signature=None,
        )
        events.append(cancel_event)

    # Sign all events
    for event in events:
        event_dict = {
            "event_id": event.event_id,
            "workflow_id": event.workflow_id,
            "action": event.action,
            "step_id": event.step_id,
            "data": event.data,
            "timestamp": event.timestamp,
            "event_version": event.event_version,
        }

        signature = sign_event(event_dict, secret_key)
        # Update event with signature (create new instance since dataclass is frozen)
        signed_event = WorkflowEvent(
            event_id=event.event_id,
            workflow_id=event.workflow_id,
            action=event.action,
            step_id=event.step_id,
            data=event.data,
            timestamp=event.timestamp,
            event_version=event.event_version,
            signature=signature,
        )

        # Replace unsigned event with signed version
        idx = events.index(event)
        events[idx] = signed_event

    return events


async def persist_migrated_events(pool: asyncpg.Pool, events: List[WorkflowEvent]):
    """Persist migrated events to workflow_events table

    Args:
        pool: asyncpg connection pool
        events: List of WorkflowEvent objects
    """

    if not events:
        return

    async with pool.acquire() as conn:
        # Use transaction for atomicity
        async with conn.transaction():
            for event in events:
                await conn.execute(
                    """
                    INSERT INTO workflow_events (
                        event_id,
                        workflow_id,
                        action,
                        step_id,
                        data,
                        timestamp,
                        event_version,
                        signature
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    event.event_id,
                    event.workflow_id,
                    event.action,
                    event.step_id,
                    event.data,
                    datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")),
                    event.event_version,
                    event.signature,
                )


async def validate_migration(
    pool: asyncpg.Pool, workflow_id: str, legacy_state: Dict[str, Any]
) -> bool:
    """Validate migrated workflow by replaying events

    Args:
        pool: asyncpg connection pool
        workflow_id: Workflow identifier
        legacy_state: Original legacy state

    Returns:
        True if validation passes
    """

    # Load migrated events
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

    if not rows:
        print(f"  ❌ No events found for workflow: {workflow_id}")
        return False

    # Convert to WorkflowEvent objects
    events = []
    for row in rows:
        event = WorkflowEvent(
            event_id=row["event_id"],
            workflow_id=row["workflow_id"],
            action=row["action"],
            step_id=row["step_id"],
            data=row["data"],
            timestamp=row["timestamp"].isoformat() + "Z",
            event_version=row["event_version"],
            signature=row["signature"],
        )
        events.append(event)

    # Replay events
    try:
        final_state = replay_workflow(events)

        # Compare with legacy state
        legacy_steps = set(legacy_state.get("steps_completed", []))
        replayed_steps = set(final_state.get("steps_completed", []))

        if legacy_steps == replayed_steps:
            print(f"  ✅ Validation passed: {workflow_id}")
            return True
        else:
            print(
                f"  ⚠️  Step mismatch: legacy={legacy_steps}, replayed={replayed_steps}"
            )
            return False

    except Exception as e:
        print(f"  ❌ Replay failed: {e}")
        return False


async def migrate_workflow(
    pool: asyncpg.Pool,
    legacy_state: Dict[str, Any],
    secret_key: str,
    dry_run: bool = False,
) -> bool:
    """Migrate a single workflow from legacy state to events

    Args:
        pool: asyncpg connection pool
        legacy_state: Legacy workflow state
        secret_key: Secret key for event signatures
        dry_run: If True, don't persist changes

    Returns:
        True if migration successful
    """

    workflow_id = legacy_state["workflow_id"]

    print(f"\nMigrating workflow: {workflow_id}")
    print(f"  Template: {legacy_state.get('template_name', 'unknown')}")
    print(f"  Status: {legacy_state.get('status', 'unknown')}")
    print(f"  Steps completed: {len(legacy_state.get('steps_completed', []))}")

    # Generate events
    try:
        events = await backfill_events_for_workflow(pool, legacy_state, secret_key)
        print(f"  Generated {len(events)} events")
    except Exception as e:
        print(f"  ❌ Event generation failed: {e}")
        return False

    # Persist events (unless dry run)
    if not dry_run:
        try:
            await persist_migrated_events(pool, events)
            print(f"  ✅ Events persisted")
        except Exception as e:
            print(f"  ❌ Persistence failed: {e}")
            return False

        # Validate migration
        is_valid = await validate_migration(pool, workflow_id, legacy_state)

        if not is_valid:
            print(f"  ⚠️  Validation warnings (see above)")
            return False
    else:
        print(f"  🔍 Dry run - no changes persisted")

    return True


async def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Migrate workflow state to event sourcing"
    )
    parser.add_argument("--workflow-id", type=str, help="Migrate specific workflow ID")
    parser.add_argument("--all", action="store_true", help="Migrate all workflows")
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run (no changes persisted)"
    )
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate existing migrations"
    )

    args = parser.parse_args()

    # Get configuration from environment
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devtools"
    )

    secret_key = os.getenv("EVENT_SIGNATURE_SECRET", "default-secret-key")

    print(f"🔄 Workflow State Migration to Event Sourcing")
    print(f"{'=' * 60}")
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Connect to database
    try:
        pool = await asyncpg.create_pool(db_url, min_size=2, max_size=5)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1

    try:
        if args.validate_only:
            # Validation mode
            print("Validation mode - checking existing migrations\n")

            legacy_workflows = await get_legacy_workflows(pool)

            if not legacy_workflows:
                print("✅ No workflows to validate")
                return 0

            success_count = 0
            for legacy_state in legacy_workflows:
                workflow_id = legacy_state["workflow_id"]
                is_valid = await validate_migration(pool, workflow_id, legacy_state)
                if is_valid:
                    success_count += 1

            print(f"\n{'=' * 60}")
            print(f"✅ Validated {success_count}/{len(legacy_workflows)} workflows")
            return 0

        elif args.workflow_id:
            # Single workflow migration
            # Load legacy state
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM workflow_state WHERE id = $1", args.workflow_id
                )

            if not row:
                print(f"❌ Workflow not found: {args.workflow_id}")
                return 1

            legacy_state = dict(row)
            legacy_state["workflow_id"] = legacy_state["id"]

            success = await migrate_workflow(
                pool, legacy_state, secret_key, args.dry_run
            )

            return 0 if success else 1

        elif args.all:
            # Migrate all workflows
            legacy_workflows = await get_legacy_workflows(pool)

            if not legacy_workflows:
                print("✅ No workflows to migrate")
                return 0

            print(f"Found {len(legacy_workflows)} workflows to migrate\n")

            success_count = 0
            for legacy_state in legacy_workflows:
                success = await migrate_workflow(
                    pool, legacy_state, secret_key, args.dry_run
                )
                if success:
                    success_count += 1

            print(f"\n{'=' * 60}")
            print(f"✅ Migrated {success_count}/{len(legacy_workflows)} workflows")

            return 0

        else:
            parser.print_help()
            return 1

    finally:
        await pool.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

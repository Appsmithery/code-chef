#!/usr/bin/env python3
"""
Update Linear Phase 2 HITL issue to mark as complete.
"""

import asyncio
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.lib.linear_client import get_linear_client


async def main():
    """Update Phase 2 HITL issue with completion status."""
    linear = get_linear_client()
    
    if not linear.is_enabled():
        print("❌ Linear integration not available. Set LINEAR_API_KEY environment variable.")
        return 1
    
    # Phase 2 HITL issue ID from Linear
    issue_id = "b3d90ca5-386e-48f4-8665-39deb258667c"
    
    description = """## Phase 2: Human-in-the-Loop (HITL) Integration - COMPLETE

### Implementation Summary
Complete HITL approval system deployed and verified in production (droplet 45.55.173.72).

### Components Delivered
1. **Risk Assessment Engine**: 4-tier scoring (low/medium/high/critical) with automated trigger rules
2. **Approval Workflow**: Full lifecycle management with PostgreSQL persistence
3. **REST API**: 5 endpoints for approval operations (approve, reject, list, status, resume)
4. **Database Schema**: 23-column approval_requests table + audit trail + analytics views
5. **Prometheus Metrics**: 4 metric families for observability
6. **LangGraph Integration**: Interrupt nodes with pause/resume capability

### Subtasks Completed
- ✅ Task 2.1: Interrupt Configuration (Risk assessor + policies)
- ✅ Task 2.2: Taskfile Commands for HITL Operations
- ✅ Task 2.3: HITL API Endpoints (5 REST endpoints)
- ✅ Task 2.4: Prometheus Metrics Integration (4 metric families)
- ✅ Task 2.5: Database Schema & Persistence (PostgreSQL with views)

### Production Metrics (as of 2025-11-18)
- Total Requests: 4 (1 approved, 3 pending)
- Average Approval Time: 1.26 seconds
- Risk Distribution: 2 critical, 1 high, 1 medium
- All 14 containers healthy on droplet

### Artifacts
- `agent_orchestrator/main.py`: HITL API endpoints (lines 705-901)
- `shared/lib/hitl_manager.py`: Approval lifecycle manager
- `shared/lib/risk_assessor.py`: Risk scoring engine
- `config/state/approval_requests.sql`: Complete database schema
- `support/docs/_temp/HITL-implemented.md`: Implementation runbook

### Testing
✅ End-to-end approval flow verified
✅ Rejection workflow tested
✅ Database persistence validated
✅ Metrics export confirmed
✅ Role-based authorization working

**Status**: Production-ready and operational
**Deployment**: https://agent.appsmithery.co (45.55.173.72)
"""
    
    print(f"📝 Updating Linear issue {issue_id}...")
    
    # Get the completed state ID by fetching workflow states
    # For now, we'll just update the description
    success = await linear.update_issue(
        issue_id,
        description=description
    )
    
    if success:
        print("✅ Successfully updated Phase 2 HITL issue in Linear")
        print(f"   Issue URL: https://linear.app/vibecoding-roadmap/issue/PR-53")
        return 0
    else:
        print("❌ Failed to update issue")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

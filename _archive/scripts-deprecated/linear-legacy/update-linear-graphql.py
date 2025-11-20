#!/usr/bin/env python3
"""
Update Linear Phase 2 HITL issue using GraphQL API directly.
"""

import asyncio
import json
import os
import sys
import aiohttp


async def update_linear_issue(issue_id: str, description: str, api_key: str):
    """Update Linear issue using GraphQL mutation."""
    
    mutation = """
    mutation IssueUpdate($id: String!, $description: String!) {
      issueUpdate(id: $id, input: { description: $description }) {
        success
        issue {
          id
          title
          url
        }
      }
    }
    """
    
    variables = {
        "id": issue_id,
        "description": description
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.linear.app/graphql",
            json={"query": mutation, "variables": variables},
            headers=headers
        ) as response:
            result = await response.json()
            
            if response.status != 200:
                print(f"❌ API error: {response.status}")
                print(json.dumps(result, indent=2))
                return False
            
            if "errors" in result:
                print(f"❌ GraphQL errors:")
                print(json.dumps(result["errors"], indent=2))
                return False
            
            if result.get("data", {}).get("issueUpdate", {}).get("success"):
                issue = result["data"]["issueUpdate"]["issue"]
                print(f"✅ Successfully updated: {issue['title']}")
                print(f"   URL: {issue['url']}")
                return True
            else:
                print("❌ Update failed")
                print(json.dumps(result, indent=2))
                return False


async def main():
    """Update Phase 2 HITL issue with completion status."""
    
    # Get API key from environment
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY environment variable not set")
        print("   Get your API key from: https://linear.app/vibecoding-roadmap/settings/api")
        return 1
    
    # Phase 2 HITL issue ID
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
    
    success = await update_linear_issue(issue_id, description, api_key)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

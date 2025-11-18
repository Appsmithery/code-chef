#!/usr/bin/env python3
"""
Create new HITL subtasks in Linear project.
"""

import asyncio
import json
import os
import sys
import aiohttp


async def create_linear_issue(
    title: str,
    description: str,
    project_id: str,
    parent_id: str,
    api_key: str,
    team_id: str = "d84426da-389b-421e-ad1a-92f79222439d"  # Team ID from roadmap
):
    """Create Linear issue using GraphQL mutation."""
    
    mutation = """
    mutation IssueCreate(
      $title: String!
      $description: String
      $projectId: String
      $parentId: String
      $teamId: String!
    ) {
      issueCreate(
        input: {
          title: $title
          description: $description
          projectId: $projectId
          parentId: $parentId
          teamId: $teamId
        }
      ) {
        success
        issue {
          id
          title
          identifier
          url
        }
      }
    }
    """
    
    variables = {
        "title": title,
        "description": description,
        "projectId": project_id,
        "parentId": parent_id,
        "teamId": team_id
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
                return None
            
            if "errors" in result:
                print(f"❌ GraphQL errors:")
                print(json.dumps(result["errors"], indent=2))
                return None
            
            if result.get("data", {}).get("issueCreate", {}).get("success"):
                issue = result["data"]["issueCreate"]["issue"]
                return issue
            else:
                print("❌ Create failed")
                print(json.dumps(result, indent=2))
                return None


async def get_team_id(api_key: str):
    """Get first team ID from workspace."""
    
    query = """
    query Teams {
      teams {
        nodes {
          id
          name
          key
        }
      }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.linear.app/graphql",
            json={"query": query},
            headers=headers
        ) as response:
            result = await response.json()
            
            if response.status == 200 and "data" in result:
                teams = result["data"]["teams"]["nodes"]
                if teams:
                    print(f"📋 Available teams:")
                    for team in teams:
                        print(f"   - {team['name']} ({team['key']}): {team['id']}")
                    return teams[0]["id"]
            
            return None


async def main():
    """Create HITL subtasks in Linear."""
    
    # Get API key from environment
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY environment variable not set")
        return 1
    
    # Project and parent IDs
    project_id = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform
    parent_id = "b3d90ca5-386e-48f4-8665-39deb258667c"   # Phase 2 HITL
    
    # Get team ID
    print("🔍 Fetching team information...")
    team_id = await get_team_id(api_key)
    if not team_id:
        print("❌ Could not determine team ID")
        return 1
    
    print(f"\n📝 Using team ID: {team_id}")
    
    # New subtasks to create
    subtasks = [
        {
            "title": "Task 2.3: HITL API Endpoints",
            "description": """Complete REST API for HITL approval workflow management.

**Endpoints Implemented:**
- `POST /approve/{approval_id}` - Approve pending requests (with role validation)
- `POST /reject/{approval_id}` - Reject requests with reason
- `GET /approvals/pending` - List pending approvals (filterable by role)
- `GET /approvals/{approval_id}` - Get approval status
- `POST /resume/{task_id}` - Resume workflow after approval

**Features:**
- Role-based authorization (ops-lead, security-admin, etc.)
- JSON request/response with Pydantic validation
- Comprehensive error handling
- Integration with hitl_manager for lifecycle operations

**Status**: ✅ Complete and tested
**Location**: `agent_orchestrator/main.py` lines 705-901
"""
        },
        {
            "title": "Task 2.4: Prometheus Metrics Integration",
            "description": """Complete observability for HITL approval system.

**Metrics Implemented:**
- `orchestrator_approval_requests_total{risk_level}` - Total requests by risk tier
- `orchestrator_approval_wait_seconds{risk_level}` - Wait time histogram
- `orchestrator_approval_decisions_total{decision,risk_level}` - Approved/rejected counts
- `orchestrator_approval_expirations_total{risk_level}` - Expired requests counter

**Production Test Results:**
- 1 critical approval request created
- 1 approval decision recorded (approved)
- 1.26 second approval wait time captured
- All metrics exported to Prometheus on port 9090

**Status**: ✅ Complete and validated
**Location**: `agent_orchestrator/main.py` (Prometheus instrumentation)
"""
        },
        {
            "title": "Task 2.5: Database Schema & Persistence",
            "description": """PostgreSQL schema for HITL approval persistence and audit trail.

**Tables:**
- `approval_requests`: 23 columns including risk metadata, approver details, JSONB fields
- `approval_actions`: Complete audit trail with foreign key constraints

**Views:**
- `pending_approvals`: Active requests with countdown timers and risk-based sorting
- `approval_statistics`: 30-day historical metrics with avg resolution time

**Indexes:**
- status, workflow_id, created_at, risk_level, expires_at for query performance

**Production State (2025-11-18):**
- Total Requests: 4 (1 approved, 3 pending)
- Average Resolution: 1.26 seconds
- Risk Distribution: 2 critical, 1 high, 1 medium

**Status**: ✅ Complete and deployed
**Location**: `config/state/approval_requests.sql`
"""
        }
    ]
    
    print(f"\n📦 Creating {len(subtasks)} new subtasks...\n")
    
    created_count = 0
    for subtask in subtasks:
        print(f"Creating: {subtask['title']}")
        issue = await create_linear_issue(
            title=subtask["title"],
            description=subtask["description"],
            project_id=project_id,
            parent_id=parent_id,
            api_key=api_key,
            team_id=team_id
        )
        
        if issue:
            print(f"✅ Created: {issue['identifier']} - {issue['title']}")
            print(f"   URL: {issue['url']}\n")
            created_count += 1
        else:
            print(f"❌ Failed to create subtask\n")
    
    print(f"\n✨ Summary: Created {created_count}/{len(subtasks)} subtasks")
    
    return 0 if created_count == len(subtasks) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

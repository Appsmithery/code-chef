#!/usr/bin/env python3
"""Create LangGraph architecture rebuild issue in Linear with sub-issues."""

import os
import requests

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY", "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571")
GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"
PROJECT_UUID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform
TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"  # Project Roadmaps

# Workflow states
IN_PROGRESS = "96689f62-1d2c-4db0-8c7a-a2bcba1a61ef"
TODO = "9b9b5687-666b-4bcb-9ebd-ecf48304a26b"

def graphql_request(query: str, variables: dict = None):
    """Execute GraphQL request."""
    headers = {
        "Authorization": LINEAR_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(
        GRAPHQL_ENDPOINT,
        json={"query": query, "variables": variables or {}},
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def create_parent_issue():
    """Create parent issue for LangGraph architecture rebuild."""
    description = """## Objective

Replace microservices architecture with LangGraph-based multi-agent workflow in single container to reduce resource usage from 900MB to 150MB baseline while preserving all multi-agent capabilities.

## Current Problem
- 6 FastAPI containers consuming 900MB+ RAM baseline
- 100% CPU/memory thrashing on 2GB droplet
- 30min build time (6 separate images)
- HTTP overhead between agents

## Solution
- Single orchestrator container with 6 LangGraph agent nodes
- Per-agent YAML configs (model, tools, prompts)
- Supervisor pattern with LLM routing
- HITL approval nodes with Linear integration
- State persistence with PostgreSQL

## Expected Outcomes
- Memory: 900MB → 150MB (83% reduction)
- CPU: Stable <1.0 avg (currently thrashing at 100%)
- Build time: 30min → 5min
- Latency: 50% reduction (no HTTP serialization)

## Implementation Phases
See sub-issues for detailed breakdown of 4-phase implementation."""

    mutation = """
    mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                id
                identifier
                title
                url
            }
        }
    }
    """
    
    variables = {
        "input": {
            "title": "🔄 LangGraph Multi-Agent Architecture Rebuild",
            "description": description,
            "teamId": TEAM_ID,
            "projectId": PROJECT_UUID,
            "stateId": IN_PROGRESS,
            "priority": 1  # Urgent
        }
    }
    
    result = graphql_request(mutation, variables)
    if result.get("data", {}).get("issueCreate", {}).get("success"):
        issue = result["data"]["issueCreate"]["issue"]
        print(f"✅ Created parent issue: {issue['identifier']} - {issue['title']}")
        print(f"   URL: {issue['url']}")
        return issue["id"]
    else:
        print(f"❌ Failed to create parent issue: {result}")
        return None

def create_sub_issue(parent_id: str, title: str, description: str):
    """Create sub-issue under parent."""
    mutation = """
    mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                id
                identifier
                title
            }
        }
    }
    """
    
    variables = {
        "input": {
            "title": title,
            "description": description,
            "teamId": TEAM_ID,
            "projectId": PROJECT_UUID,
            "parentId": parent_id,
            "stateId": TODO
        }
    }
    
    result = graphql_request(mutation, variables)
    if result.get("data", {}).get("issueCreate", {}).get("success"):
        issue = result["data"]["issueCreate"]["issue"]
        print(f"   ✅ Created sub-issue: {issue['identifier']} - {title}")
        return issue["id"]
    else:
        print(f"   ❌ Failed to create sub-issue '{title}': {result}")
        return None

def main():
    """Create parent issue and all sub-issues."""
    print("Creating LangGraph architecture rebuild issues in Linear...\n")
    
    # Create parent issue
    parent_id = create_parent_issue()
    if not parent_id:
        return
    
    print("\nCreating sub-issues...")
    
    # Phase 1: Agent Node Classes (6 sub-issues)
    sub_issues = [
        {
            "title": "Phase 1.1: Create supervisor agent node",
            "description": """Implement `agent_orchestrator/agents/supervisor.py`:
- Load config from `tools/supervisor_tools.yaml`
- Initialize with llama-3.1-70b model
- Implement routing logic (analyze task → select next agent)
- Add LangSmith tracing with project: agents-supervisor"""
        },
        {
            "title": "Phase 1.2: Create feature-dev agent node",
            "description": """Implement `agent_orchestrator/agents/feature_dev.py`:
- Load config from `tools/feature_dev_tools.yaml`
- Initialize with codellama-13b model
- Bind tools: github, filesystem, git, docker
- Progressive strategy: MINIMAL"""
        },
        {
            "title": "Phase 1.3: Create code-review agent node",
            "description": """Implement `agent_orchestrator/agents/code_review.py`:
- Load config from `tools/code_review_tools.yaml`
- Initialize with llama-3.1-70b model
- Bind tools: github, sonarqube, git
- Progressive strategy: AGENT_PROFILE"""
        },
        {
            "title": "Phase 1.4: Create infrastructure agent node",
            "description": """Implement `agent_orchestrator/agents/infrastructure.py`:
- Load config from `tools/infrastructure_tools.yaml`
- Initialize with llama-3.1-8b model
- Bind tools: terraform, kubernetes, docker"""
        },
        {
            "title": "Phase 1.5: Create cicd agent node",
            "description": """Implement `agent_orchestrator/agents/cicd.py`:
- Load config from `tools/cicd_tools.yaml`
- Initialize with llama-3.1-8b model
- Bind tools: jenkins, github-actions, docker"""
        },
        {
            "title": "Phase 1.6: Create documentation agent node",
            "description": """Implement `agent_orchestrator/agents/documentation.py`:
- Load config from `tools/documentation_tools.yaml`
- Initialize with mistral-7b model
- Bind tools: confluence, markdown, filesystem"""
        },
        {
            "title": "Phase 2: Build LangGraph workflow",
            "description": """Create `agent_orchestrator/graph.py`:
- Define WorkflowState TypedDict (messages, current_agent, task_result, approvals)
- Create StateGraph with 6 agent nodes
- Add conditional edges (supervisor → agents → supervisor)
- Implement HITL approval nodes (interrupt graph, wait for Linear notification)
- Add PostgreSQL checkpointing for workflow resume
- Set entry point to supervisor
- Compile and export `app = workflow.compile()`"""
        },
        {
            "title": "Phase 3: Update Docker Compose",
            "description": """Modify `deploy/docker-compose.yml`:
- Remove services: feature-dev, code-review, infrastructure, cicd, documentation
- Keep services: orchestrator, gateway-mcp, postgres, redis
- Update orchestrator volumes:
  - `./agent_orchestrator/tools:/app/tools:ro`
  - `./shared:/app/shared:ro`
- Set GRADIENT_MODEL=llama-3.1-70b (supervisor)
- Verify health endpoints after restart"""
        },
        {
            "title": "Phase 4: Testing & Deployment",
            "description": """Test and deploy LangGraph architecture:
- Local testing:
  - Test multi-agent workflow routing
  - Validate tool isolation per agent
  - Test HITL approval flow with Linear notifications
  - Verify checkpointing and workflow resume
- Droplet deployment:
  - Build image locally: `docker build -t orchestrator:langgraph`
  - Push to GHCR: `docker push ghcr.io/appsmithery/dev-tools-orchestrator:langgraph`
  - Deploy: `ssh droplet && docker pull && docker compose up -d`
- Validation:
  - Monitor resource usage (target: <500MB RAM, <1 CPU avg)
  - Verify LangSmith traces for all agents
  - Test approval notifications to Linear
  - Validate workflow state persistence"""
        }
    ]
    
    for sub_issue in sub_issues:
        create_sub_issue(parent_id, sub_issue["title"], sub_issue["description"])
    
    print("\n✅ All issues created successfully!")
    print(f"\nView parent issue: https://linear.app/project-roadmaps/issue/PR-XXX")

if __name__ == "__main__":
    main()

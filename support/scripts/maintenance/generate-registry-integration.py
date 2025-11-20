"""
Script to add agent registry integration to remaining agents.
This will be executed to update all agent main.py files.
"""

import os

# Agent configurations
AGENTS = [
    {
        "id": "code-review",
        "name": "Code Review Agent",
        "port": "8003",
        "capabilities": [
            {
                "name": "review_pr",
                "description": "Review pull request for code quality and security",
                "parameters": {"repo_url": "str", "pr_number": "int"},
                "cost_estimate": "~100 tokens",
                "tags": ["git", "security", "code-quality"]
            },
            {
                "name": "static_analysis",
                "description": "Perform static code analysis on diffs",
                "parameters": {"diff": "str", "language": "str"},
                "cost_estimate": "~50 tokens",
                "tags": ["analysis", "code-quality"]
            }
        ]
    },
    {
        "id": "feature-dev",
        "name": "Feature Development Agent",
        "port": "8002",
        "capabilities": [
            {
                "name": "implement_feature",
                "description": "Implement new feature from specification",
                "parameters": {"spec": "str", "repo_url": "str"},
                "cost_estimate": "~200 tokens",
                "tags": ["development", "coding", "feature"]
            },
            {
                "name": "generate_code",
                "description": "Generate code from natural language description",
                "parameters": {"description": "str", "language": "str"},
                "cost_estimate": "~150 tokens",
                "tags": ["codegen", "development"]
            }
        ]
    },
    {
        "id": "infrastructure",
        "name": "Infrastructure Agent",
        "port": "8004",
        "capabilities": [
            {
                "name": "deploy_service",
                "description": "Deploy service to specified environment",
                "parameters": {"service": "str", "environment": "str", "version": "str"},
                "cost_estimate": "~30s compute",
                "tags": ["deployment", "infrastructure", "devops"]
            },
            {
                "name": "provision_resources",
                "description": "Provision cloud infrastructure resources",
                "parameters": {"spec": "dict", "provider": "str"},
                "cost_estimate": "~60s compute",
                "tags": ["infrastructure", "cloud", "iac"]
            }
        ]
    },
    {
        "id": "cicd",
        "name": "CI/CD Agent",
        "port": "8005",
        "capabilities": [
            {
                "name": "run_tests",
                "description": "Run test suite for repository",
                "parameters": {"repo_url": "str", "commit_sha": "str"},
                "cost_estimate": "~60s compute",
                "tags": ["testing", "ci", "qa"]
            },
            {
                "name": "build_pipeline",
                "description": "Build and package application",
                "parameters": {"repo_url": "str", "build_config": "dict"},
                "cost_estimate": "~120s compute",
                "tags": ["build", "ci", "pipeline"]
            }
        ]
    },
    {
        "id": "documentation",
        "name": "Documentation Agent",
        "port": "8006",
        "capabilities": [
            {
                "name": "generate_docs",
                "description": "Generate documentation from code",
                "parameters": {"repo_url": "str", "format": "str"},
                "cost_estimate": "~150 tokens",
                "tags": ["documentation", "generation", "api"]
            },
            {
                "name": "generate_user_guide",
                "description": "Generate user guide from specifications",
                "parameters": {"spec": "str", "format": "str"},
                "cost_estimate": "~200 tokens",
                "tags": ["documentation", "user-guide"]
            }
        ]
    }
]

# Generate lifespan handler template
def generate_lifespan_handler(agent):
    capabilities_code = "[\n"
    for cap in agent["capabilities"]:
        capabilities_code += f"""        AgentCapability(
            name="{cap['name']}",
            description="{cap['description']}",
            parameters={cap['parameters']},
            cost_estimate="{cap['cost_estimate']}",
            tags={cap['tags']}
        ),\n"""
    capabilities_code += "    ]"
    
    return f'''
# Lifespan event handler for agent registry
from contextlib import asynccontextmanager
from lib.registry_client import RegistryClient, AgentCapability

registry_client: Optional[RegistryClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup/shutdown"""
    # Startup: Register with agent registry
    registry_url = os.getenv("AGENT_REGISTRY_URL", "http://agent-registry:8009")
    agent_id = "{agent['id']}"
    agent_name = "{agent['name']}"
    base_url = f"http://{agent['id']}:{{os.getenv('PORT', '{agent['port']})}}"
    
    global registry_client
    registry_client = RegistryClient(
        registry_url=registry_url,
        agent_id=agent_id,
        agent_name=agent_name,
        base_url=base_url
    )
    
    # Define capabilities
    capabilities = {capabilities_code}
    
    # Register and start heartbeat
    try:
        await registry_client.register(capabilities)
        await registry_client.start_heartbeat()
        logger.info(f"✅ Registered {{agent_id}} with agent registry")
    except Exception as e:
        logger.warning(f"⚠️  Failed to register with agent registry: {{e}}")
    
    yield
    
    # Shutdown: Stop heartbeat
    try:
        await registry_client.stop_heartbeat()
        await registry_client.close()
        logger.info(f"🛑 Unregistered {{agent_id}} from agent registry")
    except Exception as e:
        logger.warning(f"⚠️  Failed to unregister from agent registry: {{e}}")
'''

# Print generated code for each agent
for agent in AGENTS:
    print(f"\n{'='*80}")
    print(f"Agent: {agent['name']} ({agent['id']})")
    print('='*80)
    print(generate_lifespan_handler(agent))

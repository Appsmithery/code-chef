# Agent Phase 6 Feature Injection Script
# Automatically updates agent main.py files with registry, event bus, and LangGraph infrastructure

param(
    [string]$Agent = "all",
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$agentConfigs = @{
    "orchestrator" = @{
        port = 8001
        capabilities = @(
            'AgentCapability(name="decompose_task", description="Break down complex tasks into sub-tasks", parameters={"task_description": "str"}, cost_estimate="~5s compute", tags=["orchestration", "planning"])',
            'AgentCapability(name="delegate_task", description="Delegate task to specialized agent", parameters={"task_id": "str", "target_agent": "str"}, cost_estimate="~2s compute", tags=["delegation"])',
            'AgentCapability(name="approve_change", description="Review and approve/reject changes", parameters={"change_id": "str"}, cost_estimate="~10s compute", tags=["approval", "hitl"])'
        )
        requests = @("DECOMPOSE_TASK", "DELEGATE_TASK", "GET_STATUS")
    }
    "feature-dev" = @{
        port = 8002
        capabilities = @(
            'AgentCapability(name="generate_code", description="Generate code from requirements", parameters={"requirements": "str", "language": "str"}, cost_estimate="~30s compute", tags=["code-gen", "implementation"])',
            'AgentCapability(name="implement_feature", description="Implement feature end-to-end", parameters={"feature_spec": "str"}, cost_estimate="~120s compute", tags=["feature", "development"])',
            'AgentCapability(name="write_tests", description="Generate unit tests for code", parameters={"code": "str"}, cost_estimate="~20s compute", tags=["testing", "quality"])'
        )
        requests = @("GENERATE_CODE", "IMPLEMENT_FEATURE", "GET_STATUS")
    }
    "code-review" = @{
        port = 8003
        capabilities = @(
            'AgentCapability(name="review_code", description="Review code for quality and best practices", parameters={"code": "str", "context": "str"}, cost_estimate="~45s compute", tags=["review", "quality"])',
            'AgentCapability(name="security_scan", description="Scan code for security vulnerabilities", parameters={"code": "str"}, cost_estimate="~30s compute", tags=["security", "scanning"])',
            'AgentCapability(name="suggest_improvements", description="Suggest code improvements", parameters={"code": "str"}, cost_estimate="~25s compute", tags=["optimization"])'
        )
        requests = @("REVIEW_CODE", "SUGGEST_IMPROVEMENTS", "GET_STATUS")
    }
    "infrastructure" = @{
        port = 8004
        capabilities = @(
            'AgentCapability(name="provision_resource", description="Provision cloud resources", parameters={"resource_type": "str", "config": "dict"}, cost_estimate="~60s compute", tags=["provisioning", "infrastructure"])',
            'AgentCapability(name="update_config", description="Update infrastructure configuration", parameters={"service": "str", "config": "dict"}, cost_estimate="~30s compute", tags=["configuration"])',
            'AgentCapability(name="setup_monitoring", description="Configure monitoring and alerts", parameters={"service": "str"}, cost_estimate="~45s compute", tags=["observability"])'
        )
        requests = @("PROVISION_RESOURCE", "UPDATE_CONFIG", "GET_STATUS")
    }
    "documentation" = @{
        port = 8006
        capabilities = @(
            'AgentCapability(name="generate_docs", description="Generate documentation from code", parameters={"code": "str", "format": "str"}, cost_estimate="~40s compute", tags=["documentation", "generation"])',
            'AgentCapability(name="update_readme", description="Update README with changes", parameters={"changes": "list"}, cost_estimate="~20s compute", tags=["readme", "docs"])',
            'AgentCapability(name="create_diagram", description="Generate architecture diagrams", parameters={"components": "list"}, cost_estimate="~30s compute", tags=["diagrams", "visualization"])'
        )
        requests = @("GENERATE_DOCS", "UPDATE_README", "GET_STATUS")
    }
}

$agents = if ($Agent -eq "all") {
    $agentConfigs.Keys
} else {
    @($Agent)
}

# Template for LangGraph infrastructure
$langraphTemplate = @'
# LangGraph Infrastructure
try:
    import sys
    sys.path.insert(0, '/app')
    from lib.langgraph_base import get_postgres_checkpointer, create_workflow_config
    from lib.qdrant_client import get_qdrant_client
    from lib.langchain_memory import create_hybrid_memory

    checkpointer = get_postgres_checkpointer()
    qdrant_client = get_qdrant_client()
    hybrid_memory = create_hybrid_memory()
    logger.info("✓ LangGraph infrastructure initialized (PostgreSQL checkpointer + Qdrant Cloud + Hybrid memory)")
except Exception as e:
    logger.warning(f"LangGraph infrastructure unavailable: {e}")
    checkpointer = None
    qdrant_client = None
    hybrid_memory = None

# Agent registry client
registry_client: RegistryClient | None = None
'@

# Template for lifespan manager
$lifespanTemplate = @'
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Register with agent registry
    registry_url = os.getenv("AGENT_REGISTRY_URL", "http://agent-registry:8009")
    agent_id = "{AGENT_ID}"
    agent_name = "{AGENT_NAME}"
    base_url = f"http://{AGENT_ID}:{{os.getenv('PORT', '{PORT}')}}"

    global registry_client
    registry_client = RegistryClient(
        registry_url=registry_url,
        agent_id=agent_id,
        agent_name=agent_name,
        base_url=base_url
    )

    # Define capabilities
    capabilities = [
{CAPABILITIES}
    ]

    # Register and start heartbeat
    try:
        await registry_client.register(capabilities)
        await registry_client.start_heartbeat()
        logger.info(f"✅ Registered {{agent_id}} with agent registry")
    except Exception as e:
        logger.warning(f"⚠️  Failed to register with agent registry: {{e}}")

    # Connect to Event Bus
    event_bus = get_event_bus()
    try:
        await event_bus.connect()
        logger.info("✅ Connected to Event Bus")
    except Exception as e:
        logger.warning(f"⚠️  Failed to connect to Event Bus: {{e}}")

    yield

    # Shutdown: Stop heartbeat
    if registry_client:
        try:
            await registry_client.stop_heartbeat()
            await registry_client.close()
            logger.info(f"🛑 Unregistered {{agent_id}} from agent registry")
        except Exception as e:
            logger.warning(f"⚠️  Failed to unregister from agent registry: {{e}}")
'@

# Template for agent request endpoint
$endpointTemplate = @'

# === Agent-to-Agent Communication (Phase 6) ===

from lib.agent_events import AgentRequestEvent, AgentResponseEvent, AgentRequestType
from lib.agent_request_handler import handle_agent_request

@app.post("/agent-request", response_model=AgentResponseEvent, tags=["agent-communication"])
async def agent_request_endpoint(request: AgentRequestEvent):
    """
    Handle requests from other agents.

    Supports:
{REQUEST_TYPES_DOC}
    """
    return await handle_agent_request(
        request=request,
        handler=handle_{AGENT_ID_UNDERSCORE}_request,
        agent_name="{AGENT_ID}"
    )


async def handle_{AGENT_ID_UNDERSCORE}_request(request: AgentRequestEvent) -> Dict[str, Any]:
    """
    Process agent requests for {AGENT_ID} tasks.

    Args:
        request: AgentRequestEvent with request_type and payload

    Returns:
        Dict with result data

    Raises:
        ValueError: If request type not supported
    """
    request_type = request.request_type
    payload = request.payload

{REQUEST_HANDLERS}

    else:
        raise ValueError(f"Unsupported request type: {{request_type}}")
'@

Write-Host "🚀 Phase 6 Feature Injection" -ForegroundColor Cyan
Write-Host "==========================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "⚠️  DRY RUN MODE - No files will be modified`n" -ForegroundColor Yellow
}

foreach ($agentId in $agents) {
    $config = $agentConfigs[$agentId]
    $mainPath = "agent_$agentId/main.py"

    Write-Host "Processing $agentId..." -ForegroundColor Yellow

    if (-not (Test-Path $mainPath)) {
        Write-Host "  ❌ $mainPath not found`n" -ForegroundColor Red
        continue
    }

    # Read current main.py
    $content = Get-Content $mainPath -Raw

    # Check if already has Phase 6 features
    if ($content -match "registry_client: RegistryClient") {
        Write-Host "  ⏭️  Already has Phase 6 features`n" -ForegroundColor Gray
        continue
    }

    $modified = $false

    # 1. Inject imports
    if ($content -notmatch "from lib.event_bus import") {
        $importBlock = @"
from contextlib import asynccontextmanager
from lib.event_bus import get_event_bus
from lib.registry_client import RegistryClient, AgentCapability

"@
        $content = $content -replace "(from prometheus_fastapi_instrumentator import Instrumentator)", "$importBlock`$1"
        Write-Host "  ✅ Injected imports" -ForegroundColor Green
        $modified = $true
    }

    # 2. Inject LangGraph infrastructure (before app = FastAPI)
    if ($content -match "app = FastAPI\(" -and $content -notmatch "checkpointer = get_postgres_checkpointer") {
        $insertPos = $content.IndexOf("app = FastAPI(")
        $before = $content.Substring(0, $insertPos)
        $after = $content.Substring($insertPos)

        $content = $before + $langraphTemplate + "`n`n" + $after
        Write-Host "  ✅ Injected LangGraph infrastructure" -ForegroundColor Green
        $modified = $true
    }

    # 3. Replace app initialization with lifespan
    if ($content -match 'app = FastAPI\([^)]*\)' -and $content -notmatch 'lifespan=lifespan') {
        # First inject the lifespan function (before app = FastAPI)
        $appPos = $content.IndexOf("app = FastAPI(")
        $before = $content.Substring(0, $appPos)
        $after = $content.Substring($appPos)

        # Replace template placeholders
        $agentName = (Get-Culture).TextInfo.ToTitleCase($agentId -replace "-", " ") + " Agent"
        $capabilitiesStr = ($config.capabilities | ForEach-Object { "        $_" }) -join ",`n"

        $lifespan = $lifespanTemplate `
            -replace "\{AGENT_ID\}", $agentId `
            -replace "\{AGENT_NAME\}", $agentName `
            -replace "\{PORT\}", $config.port.ToString() `
            -replace "\{CAPABILITIES\}", $capabilitiesStr

        $content = $before + $lifespan + "`n`n" + $after

        # Update FastAPI initialization
        $content = $content -replace '(app = FastAPI\([^)]*)\)', '$1,`n    lifespan=lifespan`n)'

        Write-Host "  ✅ Added lifespan context manager" -ForegroundColor Green
        $modified = $true
    }

    # 4. Inject agent-request endpoint (before if __name__)
    if ($content -match "if __name__" -and $content -notmatch "/agent-request") {
        $mainPos = $content.IndexOf("if __name__")
        $before = $content.Substring(0, $mainPos)
        $after = $content.Substring($mainPos)

        # Build request handlers
        $handlers = @()
        foreach ($reqType in $config.requests) {
            if ($reqType -eq "GET_STATUS") {
                $handler = @'
    if request_type == AgentRequestType.GET_STATUS:
        return {
            "status": "healthy",
            "capabilities": [CAPS_COUNT],
            "active_tasks": 0
        }
'@ -replace "CAPS_COUNT", $config.capabilities.Count
                $handlers += $handler
            } else {
                $handler = @'
    if request_type == AgentRequestType.REQ_TYPE:
        # TODO: Implement REQ_TYPE logic
        return {"status": "completed", "request": "REQ_TYPE"}
'@ -replace "REQ_TYPE", $reqType
                $handlers += $handler
            }
        }
        $handlersStr = $handlers -join "`n    el"

        # Build request types documentation
        $reqTypesDoc = ($config.requests | ForEach-Object { "    - $_" }) -join "`n"

        $agentIdUnderscore = $agentId -replace "-", "_"
        $endpoint = $endpointTemplate `
            -replace "\{AGENT_ID\}", $agentId `
            -replace "\{AGENT_ID_UNDERSCORE\}", $agentIdUnderscore `
            -replace "\{REQUEST_TYPES_DOC\}", $reqTypesDoc `
            -replace "\{REQUEST_HANDLERS\}", $handlersStr

        $content = $before + $endpoint + "`n`n" + $after
        Write-Host "  ✅ Injected /agent-request endpoint" -ForegroundColor Green
        $modified = $true
    }

    # Write back
    if ($modified) {
        if (-not $DryRun) {
            $content | Out-File -FilePath $mainPath -Encoding UTF8 -NoNewline
            Write-Host "  💾 Saved $mainPath" -ForegroundColor Green
        } else {
            Write-Host "  [DRY RUN] Would update $mainPath" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [INFO] No changes needed" -ForegroundColor Gray
    }

    Write-Host ""
}

Write-Host "`n==> Phase 6 injection complete!" -ForegroundColor Green

if ($DryRun) {
    Write-Host "`nTip: Run without -DryRun to apply changes" -ForegroundColor Cyan
}

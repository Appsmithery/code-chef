# DigitalOcean Gradient AI Platform Setup Script
# Configures agents to use Gradient for LLM inference

$ErrorActionPreference = "Stop"

Write-Host "`n[SETUP] DigitalOcean Gradient AI Platform Integration" -ForegroundColor Cyan
Write-Host "====================================================`n" -ForegroundColor Cyan

# =============================================================================
# Step 1: Validate Gradient API Key
# =============================================================================

Write-Host "[STEP 1] Validating Gradient API key..." -ForegroundColor Yellow

if (-not $env:GRADIENT_API_KEY) {
    Write-Host "`n[ERROR] GRADIENT_API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "`nTo get your Gradient API key:" -ForegroundColor Yellow
    Write-Host "  1. Visit: https://cloud.digitalocean.com/ai" -ForegroundColor White
    Write-Host "  2. Click 'Get Started' or 'Generate API Key'" -ForegroundColor White
    Write-Host "  3. Copy the API key (format: do-api-XXXXXXXX)" -ForegroundColor White
    Write-Host "`nThen run:" -ForegroundColor Yellow
    Write-Host "  `$env:GRADIENT_API_KEY='do-api-XXXXXXXX'" -ForegroundColor Gray
    Write-Host "  ./scripts/setup-gradient.ps1" -ForegroundColor Gray
    exit 1
}

Write-Host "  [OK] GRADIENT_API_KEY found: $($env:GRADIENT_API_KEY.Substring(0, 15))..." -ForegroundColor Green

# =============================================================================
# Step 2: Update .env Configuration
# =============================================================================

Write-Host "`n[STEP 2] Updating environment configuration..." -ForegroundColor Yellow

$envFile = "config/env/.env"

if (-not (Test-Path $envFile)) {
    Write-Host "  [ERROR] $envFile not found" -ForegroundColor Red
    exit 1
}

$envContent = Get-Content $envFile -Raw

# Check if Gradient config already exists
if ($envContent -match "GRADIENT_API_KEY") {
    Write-Host "  [SKIP] Gradient configuration already exists in .env" -ForegroundColor Yellow
    
    # Update the key if different
    if ($envContent -notmatch $env:GRADIENT_API_KEY) {
        $envContent = $envContent -replace "GRADIENT_API_KEY=.*", "GRADIENT_API_KEY=$env:GRADIENT_API_KEY"
        Set-Content -Path $envFile -Value $envContent -NoNewline
        Write-Host "  [OK] Updated GRADIENT_API_KEY" -ForegroundColor Green
    }
} else {
    # Add Gradient configuration
    $gradientConfig = @"

# DigitalOcean Gradient AI Platform
GRADIENT_API_KEY=$env:GRADIENT_API_KEY
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai
GRADIENT_MODEL=llama-3.1-8b-instruct
"@
    
    Add-Content -Path $envFile -Value $gradientConfig
    Write-Host "  [OK] Added Gradient configuration to .env" -ForegroundColor Green
}

# =============================================================================
# Step 3: Configure Agent-Specific Models
# =============================================================================

Write-Host "`n[STEP 3] Configuring agent-specific models..." -ForegroundColor Yellow

$agentModels = @{
    "orchestrator" = "llama-3.1-70b-instruct"    # Complex task decomposition
    "feature-dev" = "codellama-13b-instruct"     # Code generation
    "code-review" = "llama-3.1-70b-instruct"     # Deep analysis
    "infrastructure" = "llama-3.1-8b-instruct"   # Fast IaC generation
    "cicd" = "llama-3.1-8b-instruct"             # Pipeline configs
    "documentation" = "mistral-7b-instruct"      # Fast documentation
}

foreach ($agent in $agentModels.Keys) {
    $model = $agentModels[$agent]
    Write-Host "  [CONFIG] $agent -> $model" -ForegroundColor White
}

# =============================================================================
# Step 4: Update Docker Compose with Gradient Environment Variables
# =============================================================================

Write-Host "`n[STEP 4] Updating docker-compose.yml..." -ForegroundColor Yellow

$composeFile = "compose/docker-compose.yml"

if (-not (Test-Path $composeFile)) {
    Write-Host "  [ERROR] $composeFile not found" -ForegroundColor Red
    exit 1
}

$composeContent = Get-Content $composeFile -Raw

# Check if Gradient env vars already added
if ($composeContent -match "GRADIENT_API_KEY") {
    Write-Host "  [SKIP] Gradient environment variables already in docker-compose.yml" -ForegroundColor Yellow
} else {
    Write-Host "  [INFO] Gradient env vars need to be added manually to docker-compose.yml" -ForegroundColor Yellow
    Write-Host "  [INFO] Add to each agent service:" -ForegroundColor Yellow
    Write-Host "    - GRADIENT_API_KEY=`${GRADIENT_API_KEY}" -ForegroundColor Gray
    Write-Host "    - GRADIENT_BASE_URL=`${GRADIENT_BASE_URL:-https://api.digitalocean.com/v2/ai}" -ForegroundColor Gray
    Write-Host "    - GRADIENT_MODEL=`${GRADIENT_MODEL:-llama-3.1-8b-instruct}" -ForegroundColor Gray
}

# =============================================================================
# Step 5: Verify Agent Code Files
# =============================================================================

Write-Host "`n[STEP 5] Verifying agent code files..." -ForegroundColor Yellow

$agents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")
$allAgentsExist = $true

foreach ($agent in $agents) {
    $mainFile = "agents/$agent/main.py"
    if (Test-Path $mainFile) {
        Write-Host "  [OK] Found: $mainFile" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Missing: $mainFile" -ForegroundColor Red
        $allAgentsExist = $false
    }
}

if (-not $allAgentsExist) {
    Write-Host "`n[ERROR] Some agent files are missing" -ForegroundColor Red
    exit 1
}

# =============================================================================
# Step 6: Create Gradient Warmup Module
# =============================================================================

Write-Host "`n[STEP 6] Creating Gradient warmup module..." -ForegroundColor Yellow

$warmupFile = "agents/_shared/gradient_warmup.py"
$warmupContent = @"
"""
Gradient AI Platform Warmup Module

Prevents cold starts by periodically pinging Gradient models.
Cold starts typically take 2-5 seconds; this keeps models warm.
"""

import asyncio
import os
from typing import Optional
import httpx

GRADIENT_API_KEY = os.getenv("GRADIENT_API_KEY")
GRADIENT_BASE_URL = os.getenv("GRADIENT_BASE_URL", "https://api.digitalocean.com/v2/ai")
GRADIENT_MODEL = os.getenv("GRADIENT_MODEL", "llama-3.1-8b-instruct")
WARMUP_INTERVAL = 300  # 5 minutes


async def ping_model(model: str = GRADIENT_MODEL) -> bool:
    """Send a minimal request to keep model warm."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GRADIENT_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GRADIENT_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5
                }
            )
            
            if response.status_code == 200:
                print(f"[WARMUP] Model {model} is warm")
                return True
            else:
                print(f"[WARMUP] Failed to warm {model}: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"[WARMUP] Error warming {model}: {e}")
        return False


async def keep_warm(models: Optional[list[str]] = None):
    """Background task to keep Gradient models warm."""
    
    if not GRADIENT_API_KEY:
        print("[WARMUP] GRADIENT_API_KEY not set, skipping warmup")
        return
    
    models_to_warm = models or [GRADIENT_MODEL]
    
    print(f"[WARMUP] Starting warmup task for models: {models_to_warm}")
    print(f"[WARMUP] Interval: {WARMUP_INTERVAL} seconds")
    
    while True:
        for model in models_to_warm:
            await ping_model(model)
        
        await asyncio.sleep(WARMUP_INTERVAL)


# Optional: Start warmup as background task in FastAPI
def start_warmup_task(app, models: Optional[list[str]] = None):
    """
    Start warmup background task in FastAPI app.
    
    Usage:
        from agents._shared.gradient_warmup import start_warmup_task
        
        @app.on_event("startup")
        async def startup():
            start_warmup_task(app, models=["llama-3.1-70b-instruct"])
    """
    import asyncio
    asyncio.create_task(keep_warm(models))
"@

Set-Content -Path $warmupFile -Value $warmupContent
Write-Host "  [OK] Created $warmupFile" -ForegroundColor Green

# =============================================================================
# Summary and Next Steps
# =============================================================================

Write-Host "`n====================================================`n" -ForegroundColor Cyan
Write-Host "[SUMMARY] Gradient AI Platform Setup" -ForegroundColor Green
Write-Host "====================================================`n" -ForegroundColor Cyan

Write-Host "[CONFIGURATION]" -ForegroundColor Cyan
Write-Host "  * API Key: $($env:GRADIENT_API_KEY.Substring(0, 15))..." -ForegroundColor White
Write-Host "  * Base URL: https://api.digitalocean.com/v2/ai" -ForegroundColor White
Write-Host "  * Default Model: llama-3.1-8b-instruct" -ForegroundColor White
Write-Host "  * .env file: $envFile" -ForegroundColor White

Write-Host "`n[AGENT MODELS]" -ForegroundColor Cyan
foreach ($agent in $agentModels.Keys) {
    $model = $agentModels[$agent]
    Write-Host "  * $agent`: $model" -ForegroundColor White
}

Write-Host "`n[FILES UPDATED]" -ForegroundColor Cyan
Write-Host "  [OK] config/env/.env" -ForegroundColor Green
Write-Host "  [OK] agents/_shared/gradient_warmup.py" -ForegroundColor Green
Write-Host "  [INFO] agents/*/main.py (manual update required)" -ForegroundColor Yellow

Write-Host "`n[NEXT STEPS]" -ForegroundColor Yellow
Write-Host "  1. Update docker-compose.yml with Gradient env vars:" -ForegroundColor White
Write-Host "     - GRADIENT_API_KEY=`${GRADIENT_API_KEY}" -ForegroundColor Gray
Write-Host "     - GRADIENT_BASE_URL=`${GRADIENT_BASE_URL:-https://api.digitalocean.com/v2/ai}" -ForegroundColor Gray
Write-Host "     - GRADIENT_MODEL=`${GRADIENT_MODEL:-llama-3.1-8b-instruct}" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Update agent code with Gradient client initialization" -ForegroundColor White
Write-Host "     See: docs/DigitalOcean-Gradient-Integration.md" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Rebuild and restart agents:" -ForegroundColor White
Write-Host "     docker-compose build" -ForegroundColor Gray
Write-Host "     docker-compose up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Test inference:" -ForegroundColor White
Write-Host "     curl -X POST http://localhost:8002/implement \\" -ForegroundColor Gray
Write-Host "       -H 'Content-Type: application/json' \\" -ForegroundColor Gray
Write-Host "       -d '{""description"": ""test feature""}'" -ForegroundColor Gray
Write-Host ""
Write-Host "  5. Monitor in Langfuse:" -ForegroundColor White
Write-Host "     https://us.cloud.langfuse.com" -ForegroundColor Gray

Write-Host "`n[COST SAVINGS]" -ForegroundColor Green
Write-Host "  * Gradient Llama 3.1 8B: $0.20/1M tokens" -ForegroundColor White
Write-Host "  * OpenAI GPT-3.5 Turbo: $1.50/1M tokens (7.5x more)" -ForegroundColor White
Write-Host "  * OpenAI GPT-4: $30.00/1M tokens (150x more)" -ForegroundColor White

Write-Host "`n[OK] Gradient setup script completed!`n" -ForegroundColor Green

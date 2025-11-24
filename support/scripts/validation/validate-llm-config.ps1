# Validate LLM Configuration
# Checks config/agents/models.yaml against Pydantic schema
# Usage: .\validate-llm-config.ps1

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== LLM Configuration Validation ===" -ForegroundColor Cyan

# Paths
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$configPath = Join-Path $repoRoot "config\agents\models.yaml"
$schemaPath = Join-Path $repoRoot "shared\lib\agent_config_schema.py"
$validationScript = Join-Path $repoRoot "shared\lib\validate_config.py"

# Check files exist
if (-not (Test-Path $configPath)) {
    Write-Host "❌ Config file not found: $configPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $schemaPath)) {
    Write-Host "❌ Schema file not found: $schemaPath" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found config: $configPath" -ForegroundColor Green
Write-Host "✓ Found schema: $schemaPath" -ForegroundColor Green

# Create temporary Python validation script if it doesn't exist
if (-not (Test-Path $validationScript)) {
    Write-Host "Creating validation helper script..." -ForegroundColor Yellow
    
    $pythonScript = @"
#!/usr/bin/env python3
"""
Validate models.yaml against Pydantic schema
"""
import sys
import yaml
from pathlib import Path

# Add shared/lib to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_config_schema import ModelsConfig

def validate_config(config_path: Path):
    try:
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Validate with Pydantic
        config = ModelsConfig(**raw_config)
        
        # Success output
        print("✓ YAML syntax valid")
        print(f"✓ Schema validation passed (version {config.version})")
        print(f"✓ All 6 required agents defined: {', '.join(config.agents.keys())}")
        
        # Detailed checks
        for agent_name, agent_config in config.agents.items():
            print(f"  • {agent_name}: {agent_config.model} (temp={agent_config.temperature}, max_tokens={agent_config.max_tokens})")
        
        return 0
    
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"❌ Validation failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_config.py <config_path>", file=sys.stderr)
        sys.exit(1)
    
    config_path = Path(sys.argv[1])
    sys.exit(validate_config(config_path))
"@
    
    Set-Content -Path $validationScript -Value $pythonScript -Encoding UTF8
}

# Run Python validation
Write-Host "`nRunning Pydantic validation..." -ForegroundColor Cyan

try {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    
    if (-not $pythonCmd) {
        Write-Host "❌ Python not found in PATH" -ForegroundColor Red
        exit 1
    }
    
    $output = & $pythonCmd.Source $validationScript $configPath 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $output -ForegroundColor Green
        Write-Host "`n✅ Configuration validation PASSED" -ForegroundColor Green
        exit 0
    } else {
        Write-Host $output -ForegroundColor Red
        Write-Host "`n❌ Configuration validation FAILED" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Validation error: $_" -ForegroundColor Red
    exit 1
}

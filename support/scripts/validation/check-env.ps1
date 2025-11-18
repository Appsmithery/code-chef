#!/usr/bin/env pwsh
# Check environment variable configuration status

Write-Host "[ENV] Environment Configuration Status:"

$requiredVars = @(
    "GRADIENT_MODEL_ACCESS_KEY",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "LINEAR_OAUTH_DEV_TOKEN"
)

$envFile = "config/env/.env"

if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    foreach ($var in $requiredVars) {
        if ($content -match "(?m)^$var=") {
            Write-Host "  [OK] $var"
        } else {
            Write-Host "  [MISSING] $var"
        }
    }
} else {
    Write-Host "  [ERROR] .env file not found at $envFile"
    foreach ($var in $requiredVars) {
        Write-Host "  [MISSING] $var"
    }
}

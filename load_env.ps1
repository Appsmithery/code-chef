# Load environment variables from config/env/.env
# Usage: .\load_env.ps1

$envFile = "config/env/.env"

if (Test-Path $envFile) {
    Write-Host "Loading environment from $envFile..." -ForegroundColor Cyan
    
    $count = 0
    Get-Content $envFile | ForEach-Object {
        # Skip comments and empty lines
        if ($_ -match '^([^=]+)=(.*)$' -and -not $_.StartsWith('#') -and $_.Trim() -ne '') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, 'Process')
            $count++
        }
    }
    
    Write-Host "✅ Loaded $count environment variables" -ForegroundColor Green
    
    # Verify critical keys
    if ($env:LANGCHAIN_API_KEY) {
        Write-Host "✅ LANGCHAIN_API_KEY is set" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  LANGCHAIN_API_KEY not found in .env" -ForegroundColor Yellow
    }
    
    if ($env:OPENROUTER_API_KEY) {
        Write-Host "✅ OPENROUTER_API_KEY is set" -ForegroundColor Green
    }
    
}
else {
    Write-Host "❌ File not found: $envFile" -ForegroundColor Red
    exit 1
}

param(
    [string]$EnvFile = "config/env/.env",
    [string]$ComposeFile = "compose/docker-compose.yml",
    [string]$Profiles = "agents,infra,rag",
    [string]$Registry = "",
    [string]$ImageTag = "",
    [switch]$Push
)

function Write-Info($msg) { Write-Host "[build-all] $msg" -ForegroundColor Cyan }
function Write-Err($msg)  { Write-Error "[build-all] $msg" }

if (-not (Test-Path $EnvFile))   { Write-Err "Env file '$EnvFile' not found."; exit 1 }
if (-not (Test-Path $ComposeFile)) { Write-Err "Compose file '$ComposeFile' not found."; exit 1 }

Get-Content $EnvFile |
    Where-Object { $_ -and ($_ -notmatch '^\s*#') } |
    ForEach-Object {
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value)
        }
    }

$env:COMPOSE_PROFILES = $Profiles
if ($Registry) { $env:DOCR_REGISTRY = $Registry }
if ($ImageTag) { $env:IMAGE_TAG = $ImageTag }

Write-Info "Profiles = $Profiles"
Write-Info "Registry = $env:DOCR_REGISTRY"
Write-Info "ImageTag = $env:IMAGE_TAG"

$buildArgs = @("--env-file", $EnvFile, "-f", $ComposeFile, "build", "--pull")
Write-Info "Running: docker compose $($buildArgs -join ' ')"
docker compose @buildArgs
if ($LASTEXITCODE -ne 0) { Write-Err "Build failed."; exit $LASTEXITCODE }

if ($Push) {
    if (-not $env:DOCR_REGISTRY) { Write-Err "Set -Registry or DOCR_REGISTRY before pushing."; exit 1 }
    if (-not $env:IMAGE_TAG)     { Write-Err "Set -ImageTag or IMAGE_TAG before pushing."; exit 1 }

    $pushArgs = @("--env-file", $EnvFile, "-f", $ComposeFile, "push")
    Write-Info "Running: docker compose $($pushArgs -join ' ')"
    docker compose @pushArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Push failed. If you encountered a 401/authorization error, run 'docker login registry.digitalocean.com' (use your DO email + PAT) and rerun this script."
        exit $LASTEXITCODE
    }
}

Write-Info "Done."
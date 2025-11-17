#!/usr/bin/env pwsh
<#!
.SYNOPSIS
    Build and push DigitalOcean Container Registry images with docker compose.

.DESCRIPTION
    Wraps the documented registry workflow: verifies tooling, confirms the
    DigitalOcean token scopes via `doctl account get`, mints a short-lived
    Docker credential, then runs `docker compose build`/`push` with IMAGE_TAG
    and DOCR_REGISTRY set consistently for every service.

.PARAMETER ImageTag
    Optional explicit tag. Defaults to the current git commit (short SHA).

.PARAMETER Registry
    DOCR registry slug (default: registry.digitalocean.com/the-shop-infra).

.PARAMETER EnvFile
    Path to the compose env file (default: config/env/.env).

.PARAMETER ComposeFile
    Path to the compose spec (default: compose/docker-compose.yml).

.PARAMETER Services
    Optional array of service names to scope the build/push.

.PARAMETER RegistryLoginTtlSeconds
    Expiration window for the temporary Docker credential (default: 1800).

.PARAMETER SkipBuild
    When present, skip the compose build phase and only push.

.PARAMETER SkipRegistryLogin
    When present, assume Docker already holds valid DOCR credentials.

.PARAMETER SkipDoctlAccountCheck
    When present, skip the `doctl account get` guard.
#>

param(
    [string]$ImageTag,
    [string]$Registry,
    [string]$EnvFile = "config/env/.env",
    [string]$ComposeFile = "compose/docker-compose.yml",
    [string[]]$Services,
    [int]$RegistryLoginTtlSeconds = 1800,
    [switch]$SkipBuild,
    [switch]$SkipRegistryLogin,
    [switch]$SkipDoctlAccountCheck,
    [switch]$CleanupOnFailure = $true
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step { param($Message) Write-Host "`n[STEP] $Message" -ForegroundColor Cyan }
function Write-Info { param($Message) Write-Host "  -> $Message" -ForegroundColor Gray }
function Write-Success { param($Message) Write-Host "  [OK] $Message" -ForegroundColor Green }
function Write-Failure { param($Message) Write-Host "  [ERROR] $Message" -ForegroundColor Red }

function Get-EnvValue {
    param(
        [string]$FilePath,
        [string]$Key
    )

    if (-not (Test-Path $FilePath)) { return $null }

    $line = Get-Content $FilePath | Where-Object { $_ -notmatch '^\s*#' } |
        Where-Object { $_ -match "^\s*$Key\s*=" } |
        Select-Object -First 1

    if (-not $line) { return $null }

    $parts = $line -split '=', 2
    if ($parts.Count -lt 2) { return $null }
    return $parts[1].Trim()
}

function Resolve-DocrRegistry {
    param(
        [string]$ExplicitRegistry,
        [string]$EnvFile
    )

    if ($ExplicitRegistry) { return $ExplicitRegistry }
    if ($env:DOCR_REGISTRY) { return $env:DOCR_REGISTRY }

    $fromFile = Get-EnvValue -FilePath $EnvFile -Key "DOCR_REGISTRY"
    if ($fromFile) { return $fromFile }

    return "registry.digitalocean.com/the-shop-infra"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$originalLocation = Get-Location

try {
    Set-Location $repoRoot

    if (-not (Test-Path $EnvFile)) {
        throw "Env file not found at '$EnvFile'. Copy config/env/.env.template first."
    }

    if (-not (Test-Path $ComposeFile)) {
        throw "Compose file not found at '$ComposeFile'."
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git CLI not found. Install git before running this script."
    }

    if (-not $ImageTag) {
        Write-Info "Deriving IMAGE_TAG from current git commit..."
        $gitSha = (git rev-parse --short HEAD).Trim()
        if (-not $gitSha) {
            throw "Unable to determine git SHA; pass -ImageTag explicitly."
        }
        $ImageTag = $gitSha
    }

    $Registry = Resolve-DocrRegistry -ExplicitRegistry $Registry -EnvFile $EnvFile

    Write-Info "Using IMAGE_TAG = $ImageTag"
    Write-Info "Using DOCR registry = $Registry"

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker CLI not found. Install Docker Desktop/Engine first."
    }

    try {
        docker compose version | Out-Null
    } catch {
        throw "docker compose plugin is unavailable. Upgrade Docker to v2.20+ or install compose plugin."
    }

    $doctlCmd = Get-Command doctl -ErrorAction SilentlyContinue
    if (-not $doctlCmd) {
        $localDoctl = Join-Path $repoRoot ".bin/doctl/doctl.exe"
        if (Test-Path $localDoctl) {
            Set-Alias -Name doctl -Value $localDoctl -Scope Script
            $doctlCmd = Get-Command doctl -ErrorAction SilentlyContinue
        }
    }

    if (-not $doctlCmd) {
        throw "doctl CLI not found. Run scripts/install-doctl.ps1 or install it manually."
    }

    if (-not $SkipDoctlAccountCheck) {
        Write-Step "Validating DigitalOcean token scopes (doctl account get)..."
        doctl account get | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "doctl account get failed. Ensure the token has account:read scope."
        }
        Write-Success "DigitalOcean token accepted"
    } else {
        Write-Info "Skipping doctl account scope check"
    }

    if (-not $SkipRegistryLogin) {
        Write-Step "Minting short-lived Docker credential via doctl registry login"
        doctl registry login --expiry-seconds $RegistryLoginTtlSeconds | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "doctl registry login failed. Verify the token has registry write scope."
        }
        Write-Success "Docker credential stored (expires in $RegistryLoginTtlSeconds seconds)"
    } else {
        Write-Info "Skipping doctl registry login"
    }

    $previousImageTag = $env:IMAGE_TAG
    $previousRegistry = $env:DOCR_REGISTRY
    $env:IMAGE_TAG = $ImageTag
    $env:DOCR_REGISTRY = $Registry

    $buildSuccess = $false
    $pushSuccess = $false

    try {
        if (-not $SkipBuild) {
            Write-Step "Building images with docker compose"
            $buildArgs = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile, "build")
            if ($Services) { $buildArgs += $Services }
            & docker @buildArgs
            if ($LASTEXITCODE -ne 0) {
                throw "docker compose build failed"
            }
            $buildSuccess = $true
            Write-Success "Build completed"
        } else {
            Write-Info "Skipping build phase"
            $buildSuccess = $true
        }

        Write-Step "Pushing images to $Registry with tag $ImageTag"
        $pushArgs = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile, "push")
        if ($Services) { $pushArgs += $Services }
        & docker @pushArgs
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose push failed"
        }
        $pushSuccess = $true
        Write-Success "Push succeeded"

        # Emit build metadata on success
        Write-Step "Recording build metadata"
        $reportsDir = Join-Path $repoRoot "reports"
        if (-not (Test-Path $reportsDir)) {
            New-Item -ItemType Directory -Path $reportsDir | Out-Null
        }

        $metadata = @{
            image_tag = $ImageTag
            registry = $Registry
            services = if ($Services) { $Services } else { @("all") }
            build_time = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
            git_commit = (git rev-parse HEAD).Trim()
            build_status = "success"
        } | ConvertTo-Json -Depth 5

        $metadataPath = Join-Path $reportsDir "push-docr-metadata.json"
        $metadata | Out-File -FilePath $metadataPath -Encoding UTF8
        Write-Success "Metadata saved to $metadataPath"

    } catch {
        Write-Failure $_

        if ($CleanupOnFailure) {
            Write-Step "Running cleanup after failure"
            Write-Info "Pruning Docker builder cache..."
            docker builder prune -f 2>&1 | Out-Null
            Write-Info "Pruning dangling images..."
            docker image prune -f 2>&1 | Out-Null
            Write-Success "Cleanup completed"
        }

        throw
    } finally {
        if ($null -ne $previousImageTag) {
            $env:IMAGE_TAG = $previousImageTag
        } else {
            Remove-Item Env:IMAGE_TAG -ErrorAction SilentlyContinue
        }

        if ($null -ne $previousRegistry) {
            $env:DOCR_REGISTRY = $previousRegistry
        } else {
            Remove-Item Env:DOCR_REGISTRY -ErrorAction SilentlyContinue
        }
    }

    Write-Host "`n✨ All services are now tagged as $Registry/<service>:$ImageTag." -ForegroundColor Green
    Write-Info "Verify digests: doctl registry repository list-tags <service>"
    Write-Info "Remember: the minted Docker credential expires in $RegistryLoginTtlSeconds seconds."
}
catch {
    Write-Failure $_
    exit 1
}
finally {
    Set-Location $originalLocation
}

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
    DOCR registry slug (default: registry.digitalocean.com/the-shop).

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
    [string]$Registry = "registry.digitalocean.com/the-shop",
    [string]$EnvFile = "config/env/.env",
    [string]$ComposeFile = "compose/docker-compose.yml",
    [string[]]$Services,
    [int]$RegistryLoginTtlSeconds = 1800,
    [switch]$SkipBuild,
    [switch]$SkipRegistryLogin,
    [switch]$SkipDoctlAccountCheck
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step { param($Message) Write-Host "`n[STEP] $Message" -ForegroundColor Cyan }
function Write-Info { param($Message) Write-Host "  -> $Message" -ForegroundColor Gray }
function Write-Success { param($Message) Write-Host "  [OK] $Message" -ForegroundColor Green }
function Write-Failure { param($Message) Write-Host "  [ERROR] $Message" -ForegroundColor Red }

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

    if (-not (Get-Command doctl -ErrorAction SilentlyContinue)) {
        throw "doctl CLI not found. Run scripts/install-doctl.ps1 or install it manually."
    }

    if (-not $SkipDoctlAccountCheck) {
        Write-Step "Validating DigitalOcean token scopes (doctl account get)..."
        doctl account get | Out-Null
        Write-Success "DigitalOcean token accepted"
    } else {
        Write-Info "Skipping doctl account scope check"
    }

    if (-not $SkipRegistryLogin) {
        Write-Step "Minting short-lived Docker credential via doctl registry login"
        doctl registry login --expiry-seconds $RegistryLoginTtlSeconds | Out-Null
        Write-Success "Docker credential stored (expires in $RegistryLoginTtlSeconds seconds)"
    } else {
        Write-Info "Skipping doctl registry login"
    }

    if (-not $SkipBuild) {
        Write-Step "Building images with docker compose"
        $buildArgs = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile, "build")
        if ($Services) { $buildArgs += $Services }
        & docker @buildArgs
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose build failed"
        }
        Write-Success "Build completed"
    } else {
        Write-Info "Skipping build phase"
    }

    Write-Step "Pushing images to $Registry with tag $ImageTag"
    $previousImageTag = $env:IMAGE_TAG
    $previousRegistry = $env:DOCR_REGISTRY
    $env:IMAGE_TAG = $ImageTag
    $env:DOCR_REGISTRY = $Registry

    try {
        $pushArgs = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile, "push")
        if ($Services) { $pushArgs += $Services }
        & docker @pushArgs
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose push failed"
        }
        Write-Success "Push succeeded"
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

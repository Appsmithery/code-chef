# GitHub Actions Secrets Setup Script
# Run this to configure required secrets for frontend CI/CD

$ErrorActionPreference = "Stop"

Write-Host "🔐 GitHub Actions Secrets Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if GitHub CLI is installed
try {
    gh --version | Out-Null
}
catch {
    Write-Host "❌ GitHub CLI (gh) not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install from: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host "Or run: winget install --id GitHub.cli" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
try {
    gh auth status 2>&1 | Out-Null
}
catch {
    Write-Host "❌ Not authenticated with GitHub" -ForegroundColor Red
    Write-Host "Run: gh auth login" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ GitHub CLI authenticated" -ForegroundColor Green
Write-Host ""

# Repository info
$REPO = "Appsmithery/code-chef"

# Secret 1: DROPLET_HOST
Write-Host "1️⃣  Setting DROPLET_HOST..." -ForegroundColor Yellow
$DROPLET_HOST = "45.55.173.72"
gh secret set DROPLET_HOST --body $DROPLET_HOST --repo $REPO
Write-Host "   ✅ DROPLET_HOST = $DROPLET_HOST" -ForegroundColor Green

# Secret 2: DROPLET_USER
Write-Host ""
Write-Host "2️⃣  Setting DROPLET_USER..." -ForegroundColor Yellow
$DROPLET_USER = "root"
gh secret set DROPLET_USER --body $DROPLET_USER --repo $REPO
Write-Host "   ✅ DROPLET_USER = $DROPLET_USER" -ForegroundColor Green

# Secret 3: DROPLET_SSH_KEY
Write-Host ""
Write-Host "3️⃣  Setting DROPLET_SSH_KEY..." -ForegroundColor Yellow
Write-Host ""
Write-Host "   Finding SSH private key..." -ForegroundColor Cyan

$SSH_KEY_PATH = "$env:USERPROFILE\.ssh\id_rsa"
$SSH_KEY_ED25519 = "$env:USERPROFILE\.ssh\id_ed25519"

if (Test-Path $SSH_KEY_ED25519) {
    $SSH_KEY_PATH = $SSH_KEY_ED25519
    Write-Host "   Found: id_ed25519" -ForegroundColor Green
}
elseif (Test-Path $SSH_KEY_PATH) {
    Write-Host "   Found: id_rsa" -ForegroundColor Green
}
else {
    Write-Host "   ❌ No SSH key found" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Generate one with:" -ForegroundColor Yellow
    Write-Host "   ssh-keygen -t ed25519 -C 'github-actions-deploy'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Then add public key to droplet:" -ForegroundColor Yellow
    Write-Host "   ssh-copy-id root@45.55.173.72" -ForegroundColor Yellow
    exit 1
}

$SSH_KEY_CONTENT = Get-Content $SSH_KEY_PATH -Raw
gh secret set DROPLET_SSH_KEY --body $SSH_KEY_CONTENT --repo $REPO
Write-Host "   ✅ DROPLET_SSH_KEY uploaded" -ForegroundColor Green

# Verify secrets
Write-Host ""
Write-Host "4️⃣  Verifying secrets..." -ForegroundColor Yellow
$SECRETS = gh secret list --repo $REPO | Out-String

if ($SECRETS -match "DROPLET_HOST" -and $SECRETS -match "DROPLET_USER" -and $SECRETS -match "DROPLET_SSH_KEY") {
    Write-Host "   ✅ All secrets configured" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  Some secrets may be missing" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📋 Secret Summary:" -ForegroundColor Cyan
gh secret list --repo $REPO

Write-Host ""
Write-Host "🎉 Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Make a change to support/frontend/v3/src/pages/Home.tsx"
Write-Host "2. Commit and push to main"
Write-Host "3. Watch deployment in: https://github.com/$REPO/actions"
Write-Host ""
Write-Host "Manual trigger: gh workflow run deploy-frontend.yml" -ForegroundColor Yellow

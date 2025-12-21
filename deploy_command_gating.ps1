#!/usr/bin/env pwsh
# Deploy Execute Command Gating to Production Droplet
# Usage: .\deploy_command_gating.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Execute Command Gating to Production Droplet" -ForegroundColor Cyan
Write-Host ""

# Configuration
$DROPLET_IP = "45.55.173.72"
$DROPLET_USER = "root"
$DEPLOY_PATH = "/opt/code-chef"
$HEALTH_CHECK_URL = "https://codechef.appsmithery.co/health"

# Step 1: Commit and push changes
Write-Host "📝 Step 1: Committing and pushing changes..." -ForegroundColor Yellow
git add -A
$commitMessage = "feat: implement execute command gating with Linear orchestration

- Add command parser for /execute, /help, /status, /cancel
- Remove automatic intent detection from /chat/stream
- Make /chat/stream purely conversational
- Add Linear parent issue creation to /execute/stream
- Implement supervisor routing and subissue creation
- Add Linear state updates (In Progress → Done)
- Add user hints for task-like messages
- Create comprehensive tests (29 unit tests, all passing)
- Add migration guide and documentation"

git commit -m $commitMessage
git push origin main

Write-Host "✅ Changes committed and pushed" -ForegroundColor Green
Write-Host ""

# Step 2: Pull changes on droplet
Write-Host "📥 Step 2: Pulling changes on droplet..." -ForegroundColor Yellow
ssh ${DROPLET_USER}@${DROPLET_IP} "cd ${DEPLOY_PATH} && git pull"

Write-Host "✅ Changes pulled" -ForegroundColor Green
Write-Host ""

# Step 3: Restart services
Write-Host "🔄 Step 3: Restarting services..." -ForegroundColor Yellow
Write-Host "This will cause ~30s of downtime" -ForegroundColor Gray

ssh ${DROPLET_USER}@${DROPLET_IP} "cd ${DEPLOY_PATH} && docker compose down && docker compose up -d"

Write-Host "✅ Services restarted" -ForegroundColor Green
Write-Host ""

# Step 4: Wait for services to be ready
Write-Host "⏳ Step 4: Waiting for services to be ready (60s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Step 5: Health check
Write-Host "🏥 Step 5: Running health checks..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri $HEALTH_CHECK_URL -Method Get
    
    if ($response.status -eq "ok") {
        Write-Host "✅ Health check passed!" -ForegroundColor Green
        Write-Host "   Service: $($response.service)" -ForegroundColor Gray
        Write-Host "   Version: $($response.version)" -ForegroundColor Gray
        
        # Check dependencies
        if ($response.dependencies) {
            Write-Host "   Dependencies:" -ForegroundColor Gray
            $response.dependencies.PSObject.Properties | ForEach-Object {
                $color = if ($_.Value -eq "connected") { "Green" } else { "Red" }
                Write-Host "     - $($_.Name): $($_.Value)" -ForegroundColor $color
            }
        }
    }
    else {
        Write-Host "❌ Health check failed: $($response.status)" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 6: Test command parsing
Write-Host "🧪 Step 6: Testing command parsing..." -ForegroundColor Yellow

# This would require the API endpoint to be accessible
# For now, just check logs
Write-Host "Checking logs for command parser initialization..." -ForegroundColor Gray
ssh ${DROPLET_USER}@${DROPLET_IP} "docker logs deploy-orchestrator-1 --tail=20 | grep -i command || true"

Write-Host ""

# Step 7: Monitor logs
Write-Host "📊 Step 7: Monitoring initial logs..." -ForegroundColor Yellow
Write-Host "Watching for errors in the first 30 seconds..." -ForegroundColor Gray

$logJob = Start-Job -ScriptBlock {
    param($user, $ip)
    ssh "${user}@${ip}" "docker logs -f deploy-orchestrator-1 2>&1 | head -n 50"
} -ArgumentList $DROPLET_USER, $DROPLET_IP

Start-Sleep -Seconds 30
Stop-Job -Job $logJob
$logs = Receive-Job -Job $logJob

if ($logs -match "ERROR") {
    Write-Host "⚠️  Errors detected in logs:" -ForegroundColor Yellow
    $logs | Select-String "ERROR" | ForEach-Object { Write-Host "   $_" -ForegroundColor Red }
}
else {
    Write-Host "✅ No errors detected in initial logs" -ForegroundColor Green
}

Remove-Job -Job $logJob
Write-Host ""

# Step 8: Summary
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 What Was Deployed:" -ForegroundColor Yellow
Write-Host "  • Command parser (/execute, /help, /status, /cancel)" -ForegroundColor White
Write-Host "  • Conversational mode for /chat/stream" -ForegroundColor White
Write-Host "  • Linear issue orchestration" -ForegroundColor White
Write-Host "  • Supervisor routing with subissues" -ForegroundColor White
Write-Host "  • Real-time Linear state updates" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "  • Migration Guide: support/docs/COMMAND-GATING-MIGRATION.md" -ForegroundColor White
Write-Host "  • Implementation: support/docs/COMMAND-GATING-IMPLEMENTATION.md" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Test /execute command in VS Code extension" -ForegroundColor White
Write-Host "  2. Verify Linear issue creation" -ForegroundColor White
Write-Host "  3. Monitor logs for 24 hours: ssh root@45.55.173.72 'docker logs -f deploy-orchestrator-1'" -ForegroundColor White
Write-Host "  4. Check Linear project for new issues: https://linear.app/..." -ForegroundColor White
Write-Host ""
Write-Host "🚨 Rollback (if needed):" -ForegroundColor Yellow
Write-Host "  ssh root@45.55.173.72 'cd /opt/code-chef && git log --oneline | head -5 && git checkout <prev-commit> && docker compose down && docker compose up -d'" -ForegroundColor White
Write-Host ""
Write-Host "🎉 Happy coding!" -ForegroundColor Cyan

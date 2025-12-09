# React/TypeScript v3 Frontend Deployment Script
# Usage: .\deploy-frontend-v3.ps1
# Prerequisites: SSH access to 45.55.173.72, git credentials configured

$ErrorActionPreference = "Stop"

Write-Host "🚀 Code/Chef Frontend v3 Deployment" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

# Configuration
$DROPLET_IP = "45.55.173.72"
$DROPLET_USER = "root"
$APP_DIR = "/opt/code-chef"
$FRONTEND_DIR = "support/frontend/v3"

Write-Host "📋 Pre-deployment checks..." -ForegroundColor Cyan
Write-Host "   • Target: $DROPLET_IP"
Write-Host "   • Directory: $APP_DIR"
Write-Host "   • Frontend: $FRONTEND_DIR"
Write-Host ""

$confirmation = Read-Host "Continue with deployment? (y/n)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "❌ Deployment cancelled" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "1️⃣  Connecting to droplet..." -ForegroundColor Yellow

$sshCommands = @"
echo "2️⃣  Pulling latest changes..."
cd /opt/code-chef
git pull origin main

echo "3️⃣  Building frontend..."
cd support/frontend/v3
npm install
npm run build

echo "4️⃣  Verifying build output..."
if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist/ directory not found"
    exit 1
fi
echo "   ✅ Build successful"

echo "5️⃣  Restarting Caddy..."
cd /opt/code-chef
docker compose restart caddy

echo "6️⃣  Checking Caddy status..."
docker compose ps caddy

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔍 Verification URLs:"
echo "   • Homepage: https://codechef.appsmithery.co"
echo "   • Health: https://codechef.appsmithery.co/api/health"
echo ""
echo "📊 Next steps:"
echo "   1. Test homepage in browser"
echo "   2. Verify theme toggle works"
echo "   3. Check browser console for errors"
echo "   4. Monitor Grafana for 24 hours"
echo ""
"@

ssh "$DROPLET_USER@$DROPLET_IP" $sshCommands

Write-Host ""
Write-Host "🎉 Deployment script completed!" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  Remember to:" -ForegroundColor Yellow
Write-Host "   • Update Linear issue with deployment timestamp"
Write-Host "   • Monitor error rates in Grafana"
Write-Host "   • Test mobile responsive layout"

#!/bin/bash
# React/TypeScript v3 Frontend Deployment Script
# Usage: ./deploy-frontend-v3.sh
# Prerequisites: SSH access to 45.55.173.72, git credentials configured

set -e  # Exit on error

echo "🚀 Code/Chef Frontend v3 Deployment"
echo "===================================="
echo ""

# Configuration
DROPLET_IP="45.55.173.72"
DROPLET_USER="root"
APP_DIR="/opt/code-chef"
FRONTEND_DIR="support/frontend/v3"

echo "📋 Pre-deployment checks..."
echo "   • Target: $DROPLET_IP"
echo "   • Directory: $APP_DIR"
echo "   • Frontend: $FRONTEND_DIR"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo ""
echo "1️⃣  Connecting to droplet..."
ssh -t $DROPLET_USER@$DROPLET_IP << 'ENDSSH'

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

ENDSSH

echo ""
echo "🎉 Deployment script completed!"
echo ""
echo "⚠️  Remember to:"
echo "   • Update Linear issue with deployment timestamp"
echo "   • Monitor error rates in Grafana"
echo "   • Test mobile responsive layout"

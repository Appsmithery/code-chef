#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Grafana Cloud Agent to DigitalOcean droplet
.DESCRIPTION
    Installs and configures Grafana Cloud Agent to scrape local Prometheus metrics
    and forward to Grafana Cloud (appsmithery.grafana.net)
.PARAMETER SkipInstall
    Skip agent installation (useful if already installed)
.EXAMPLE
    .\deploy-grafana-agent.ps1
    .\deploy-grafana-agent.ps1 -SkipInstall
#>

param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$DROPLET_HOST = "codechef.appsmithery.co"
$DROPLET_IP = "45.55.173.72"  # For SSH access
$DROPLET_USER = "root"
$AGENT_VERSION = "v0.38.1"
$CONFIG_LOCAL = "config/grafana/agent-config.yaml"
$CONFIG_REMOTE = "/etc/grafana-agent/config.yaml"

Write-Host "=== Grafana Cloud Agent Deployment ===" -ForegroundColor Cyan
Write-Host "Target: $DROPLET_USER@$DROPLET_IP ($DROPLET_HOST)"
Write-Host "Version: $AGENT_VERSION"
Write-Host ""

# Test SSH connection
Write-Host "[1/6] Testing SSH connection..." -ForegroundColor Yellow
try {
    ssh -o ConnectTimeout=5 "$DROPLET_USER@$DROPLET_IP" "echo 'Connection OK'"
} catch {
    Write-Host "❌ SSH connection failed. Check your SSH keys and network." -ForegroundColor Red
    exit 1
}
Write-Host "✅ SSH connection successful" -ForegroundColor Green
Write-Host ""

if (-not $SkipInstall) {
    # Install Grafana Cloud Agent
    Write-Host "[2/6] Installing Grafana Cloud Agent..." -ForegroundColor Yellow
    
    $installScript = @"
set -e

# Download and install agent
echo "Downloading Grafana Agent ${AGENT_VERSION}..."
cd /tmp
wget -q https://github.com/grafana/agent/releases/download/${AGENT_VERSION}/grafana-agent-linux-amd64.zip
unzip -q grafana-agent-linux-amd64.zip
chmod +x grafana-agent-linux-amd64
mv grafana-agent-linux-amd64 /usr/local/bin/grafana-agent
rm grafana-agent-linux-amd64.zip

# Verify installation
/usr/local/bin/grafana-agent --version

echo "✅ Grafana Agent installed"
"@
    
    ssh "$DROPLET_USER@$DROPLET_IP" $installScript
    Write-Host "✅ Grafana Agent installed" -ForegroundColor Green
} else {
    Write-Host "[2/6] Skipping installation (already installed)" -ForegroundColor Yellow
}
Write-Host ""

# Create config directory
Write-Host "[3/6] Creating config directory..." -ForegroundColor Yellow
ssh "$DROPLET_USER@$DROPLET_IP" "mkdir -p /etc/grafana-agent /var/lib/grafana-agent/data"
Write-Host "✅ Config directory created" -ForegroundColor Green
Write-Host ""

# Upload config file
Write-Host "[4/6] Uploading configuration..." -ForegroundColor Yellow
if (-not (Test-Path $CONFIG_LOCAL)) {
    Write-Host "❌ Config file not found: $CONFIG_LOCAL" -ForegroundColor Red
    exit 1
}
scp "$CONFIG_LOCAL" "${DROPLET_USER}@${DROPLET_IP}:${CONFIG_REMOTE}"
Write-Host "✅ Configuration uploaded" -ForegroundColor Green
Write-Host ""

# Create systemd service
Write-Host "[5/6] Setting up systemd service..." -ForegroundColor Yellow

$serviceScript = @"
set -e

# Create systemd service file
cat > /etc/systemd/system/grafana-agent.service << 'EOF'
[Unit]
Description=Grafana Cloud Agent
Documentation=https://grafana.com/docs/agent/latest/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/grafana-agent -config.file=/etc/grafana-agent/config.yaml -enable-features=integrations-next
Restart=on-failure
RestartSec=10s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo "✅ Systemd service created"
"@

ssh "$DROPLET_USER@$DROPLET_IP" $serviceScript
Write-Host "✅ Systemd service configured" -ForegroundColor Green
Write-Host ""

# Start service
Write-Host "[6/6] Starting Grafana Agent..." -ForegroundColor Yellow

$startScript = @"
set -e

# Enable and start service
systemctl enable grafana-agent
systemctl restart grafana-agent

# Wait for startup
sleep 3

# Check status
systemctl status grafana-agent --no-pager || true

# Check logs
echo ""
echo "=== Recent Logs ==="
journalctl -u grafana-agent -n 20 --no-pager

echo ""
echo "✅ Grafana Agent is running"
"@

ssh "$DROPLET_USER@$DROPLET_IP" $startScript
Write-Host "✅ Grafana Agent started" -ForegroundColor Green
Write-Host ""

# Verification
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Check metrics in Grafana Cloud Explore:"
Write-Host "   https://appsmithery.grafana.net/explore"
Write-Host ""
Write-Host "2. Run test query:"
Write-Host "   up{service='orchestrator'}"
Write-Host ""
Write-Host "3. Open dashboard:"
Write-Host "   https://appsmithery.grafana.net/d/ed621f5b-cc44-43e6-be73-ab9922cb36fc"
Write-Host ""
Write-Host "4. Monitor agent logs:"
Write-Host "   ssh $DROPLET_USER@$DROPLET_IP 'journalctl -u grafana-agent -f'"
Write-Host ""
Write-Host "5. Restart agent if needed:"
Write-Host "   ssh $DROPLET_USER@$DROPLET_IP 'systemctl restart grafana-agent'"
Write-Host ""

#!/bin/bash
# Install Grafana Alloy on DigitalOcean Droplet
# Documentation: https://grafana.com/docs/alloy/latest/

set -e

echo "=== Installing Grafana Alloy ==="

# Environment variables from Grafana Cloud
export GCLOUD_HOSTED_METRICS_ID="2677183"
export GCLOUD_HOSTED_METRICS_URL="https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push"
export GCLOUD_HOSTED_LOGS_ID="1334268"
export GCLOUD_HOSTED_LOGS_URL="https://logs-prod-036.grafana.net/loki/api/v1/push"
export GCLOUD_FM_URL="https://fleet-management-prod-008.grafana.net"
export GCLOUD_FM_POLL_FREQUENCY="60s"
export GCLOUD_FM_HOSTED_ID="1376474"
export ARCH="amd64"
export GCLOUD_RW_API_KEY="glc_eyJvIjoiMTUzNDY4MSIsIm4iOiJzdGFjay0xMzc2NDc0LWhtLXdyaXRlLWdyYWZhbmFfYXBpX3Rva2VuIiwiayI6IjRydkxVNDY1cnA4NDdWTTYwd1kxY0dYVyIsIm0iOnsiciI6InByb2QtdXMtZWFzdC0wIn19"

echo "Installing Grafana Alloy..."
/bin/sh -c "$(curl -fsSL https://storage.googleapis.com/cloud-onboarding/alloy/scripts/install-linux.sh)"

echo "✅ Alloy installed successfully"
echo ""
echo "Next steps:"
echo "1. Configure Alloy: /etc/alloy/config.alloy"
echo "2. Start service: systemctl start alloy"
echo "3. Check status: systemctl status alloy"
echo "4. View logs: journalctl -u alloy -f"

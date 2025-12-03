#!/bin/bash
# Deploy minimal working Alloy config

ssh do-codechef-droplet << 'ENDSSH'
# Stop service
systemctl stop alloy
systemctl reset-failed alloy

# Create minimal working config
cat > /etc/alloy/config.alloy << 'EOF'
prometheus.remote_write "grafana_cloud" {
  endpoint {
    url = "https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push"
    
    basic_auth {
      username = "2677183"
      password = "glc_eyJvIjoiMTUzNDY4MSIsIm4iOiJzdGFjay0xMzc2NDc0LWhtLXdyaXRlLWdyYWZhbmFfYXBpX3Rva2VuIiwiayI6IjRydkxVNDY1cnA4NDdWTTYwd1kxY0dYVyIsIm0iOnsiciI6InByb2QtdXMtZWFzdC0wIn19"
    }
  }
  
  external_labels = {
    cluster = "dev-tools",
  }
}

prometheus.scrape "orchestrator" {
  targets = [
    {"__address__" = "localhost:8001"},
  ]
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
  job_name   = "orchestrator"
}

prometheus.scrape "gateway" {
  targets = [
    {"__address__" = "localhost:8000"},
  ]
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
  job_name   = "gateway-mcp"
}

prometheus.scrape "rag" {
  targets = [
    {"__address__" = "localhost:8007"},
  ]
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
  job_name   = "rag-context"
}

prometheus.scrape "state" {
  targets = [
    {"__address__" = "localhost:8008"},
  ]
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
  job_name   = "state-persistence"
}

prometheus.scrape "registry" {
  targets = [
    {"__address__" = "localhost:8009"},
  ]
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
  job_name   = "agent-registry"
}

prometheus.scrape "prometheus" {
  targets = [
    {"__address__" = "localhost:9090"},
  ]
  forward_to = [prometheus.remote_write.grafana_cloud.receiver]
  job_name   = "prometheus"
}
EOF

# Validate config
/usr/bin/alloy fmt /etc/alloy/config.alloy

# Start service
systemctl start alloy
sleep 3

# Check status
systemctl status alloy --no-pager

# Show logs
echo ""
echo "=== Recent Logs ==="
journalctl -u alloy -n 20 --no-pager
ENDSSH

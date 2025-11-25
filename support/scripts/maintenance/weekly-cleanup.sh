#!/bin/bash
#
# Weekly Docker Cleanup Script
# Runs via cron: 0 3 * * 0 (Sundays at 3 AM)
#
# Purpose: Prevent memory/disk exhaustion from accumulated Docker resources
# Location: /opt/Dev-Tools/support/scripts/maintenance/weekly-cleanup.sh
#

set -e

DEPLOY_PATH="/opt/Dev-Tools/deploy"
LOG_FILE="/var/log/docker-cleanup.log"

# Logging functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# Pre-cleanup metrics
log "🧹 Starting Weekly Docker Cleanup"
log "================================================"

log "📊 Pre-Cleanup Metrics:"
log "=== Memory Usage ==="
free -h | tee -a "$LOG_FILE"

log ""
log "=== Disk Usage ==="
df -h / | tee -a "$LOG_FILE"

log ""
log "=== Docker Disk Usage ==="
docker system df | tee -a "$LOG_FILE"

log ""
log "=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Size}}" | tee -a "$LOG_FILE"

# Perform cleanup
log ""
log "🗑️  Removing stopped containers older than 7 days..."
REMOVED_CONTAINERS=$(docker container prune -f --filter "until=168h" 2>&1 || echo "0B")
log "$REMOVED_CONTAINERS"

log ""
log "🗑️  Removing unused images older than 7 days..."
REMOVED_IMAGES=$(docker image prune -af --filter "until=168h" 2>&1 || echo "0B")
log "$REMOVED_IMAGES"

log ""
log "🗑️  Removing build cache older than 7 days..."
REMOVED_CACHE=$(docker builder prune -af --filter "until=168h" 2>&1 || echo "0B")
log "$REMOVED_CACHE"

log ""
log "🗑️  Removing unused networks..."
REMOVED_NETWORKS=$(docker network prune -f 2>&1 || echo "None")
log "$REMOVED_NETWORKS"

# Post-cleanup metrics
log ""
log "📊 Post-Cleanup Metrics:"
log "=== Memory Usage ==="
free -h | tee -a "$LOG_FILE"

log ""
log "=== Disk Usage ==="
df -h / | tee -a "$LOG_FILE"

log ""
log "=== Docker Disk Usage ==="
docker system df | tee -a "$LOG_FILE"

# Verify services are healthy
log ""
log "🔍 Verifying service health..."
cd "$DEPLOY_PATH"

# Check container status
log "=== Container Status ==="
docker compose ps | tee -a "$LOG_FILE"

# Wait for services to stabilize
sleep 10

# Check health endpoints
log ""
log "=== Health Checks ==="
HEALTH_FAILED=0
for port in 8000 8001 8007 8008 8009 8010; do
    if curl -sf http://localhost:$port/health > /dev/null 2>&1; then
        log "✓ Port $port: OK"
    else
        log_error "✗ Port $port: FAIL"
        HEALTH_FAILED=1
    fi
done

# Summary
log ""
log "================================================"
if [ $HEALTH_FAILED -eq 0 ]; then
    log "✅ Weekly cleanup completed successfully"
    log "All services are healthy"
else
    log_error "⚠️  Cleanup completed but some services are unhealthy"
    log_error "Manual intervention may be required"
fi

log "================================================"
log ""

# Rotate log if too large (>10MB)
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$LOG_SIZE" -gt 10485760 ]; then
        log "📝 Rotating log file (size: $LOG_SIZE bytes)"
        mv "$LOG_FILE" "$LOG_FILE.old"
        gzip "$LOG_FILE.old"
    fi
fi

exit $HEALTH_FAILED

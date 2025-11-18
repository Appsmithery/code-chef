#!/bin/bash
# Backup Docker volumes

set -e

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up volumes to $BACKUP_DIR..."

docker run --rm \
  -v orchestrator-data:/data \
  -v "$BACKUP_DIR:/backup" \
  alpine tar czf /backup/orchestrator-data.tar.gz -C /data .

docker run --rm \
  -v mcp-config:/data \
  -v "$BACKUP_DIR:/backup" \
  alpine tar czf /backup/mcp-config.tar.gz -C /data .

echo "Backup complete: $BACKUP_DIR"
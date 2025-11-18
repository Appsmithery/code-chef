#!/bin/bash
# Restore Docker volumes from backup

set -e

if [ -z "$1" ]; then
  echo "Usage: ./restore_volumes.sh <backup_directory>"
  exit 1
fi

BACKUP_DIR="$1"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR"
  exit 1
fi

echo "Restoring volumes from $BACKUP_DIR..."

docker run --rm \
  -v orchestrator-data:/data \
  -v "$BACKUP_DIR:/backup" \
  alpine sh -c "cd /data && tar xzf /backup/orchestrator-data.tar.gz"

docker run --rm \
  -v mcp-config:/data \
  -v "$BACKUP_DIR:/backup" \
  alpine sh -c "cd /data && tar xzf /backup/mcp-config.tar.gz"

echo "Restore complete."
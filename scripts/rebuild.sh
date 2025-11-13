#!/bin/bash
# Rebuild and restart Dev-Tools services

set -e

echo "Rebuilding Dev-Tools services..."

cd compose
docker-compose down
docker-compose build --no-cache
docker-compose up -d

echo "Rebuild complete. Services restarted."
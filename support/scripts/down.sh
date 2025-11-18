#!/bin/bash
# Bring down the Dev-Tools stack

set -e

echo "Stopping Dev-Tools services..."

cd compose
docker-compose down

echo "Services stopped."
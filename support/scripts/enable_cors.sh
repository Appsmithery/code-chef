#!/bin/bash
set -e

echo "🔧 Adding CORS to all agents..."

# Define agents
agents="orchestrator feature-dev code-review infrastructure cicd documentation"

for agent in $agents; do
    mainpy="/opt/Dev-Tools/agents/$agent/main.py"
    
    # Check if CORS already added
    if grep -q "CORSMiddleware" "$mainpy"; then
        echo "⏭️  $agent: CORS already configured"
        continue
    fi
    
    # Backup
    cp "$mainpy" "$mainpy.backup"
    
    # Create temp file with CORS added
    python3 << 'PYTHON'
import sys
with open("$mainpy", "r") as f:
    lines = f.readlines()

# Find FastAPI import and app creation
import_idx = -1
app_idx = -1
for i, line in enumerate(lines):
    if "from fastapi import FastAPI" in line and import_idx == -1:
        import_idx = i
    if line.strip().startswith("app = FastAPI") and app_idx == -1:
        app_idx = i
        # Find closing paren
        if ")" not in line:
            for j in range(i+1, len(lines)):
                if ")" in lines[j]:
                    app_idx = j
                    break

if import_idx >= 0 and app_idx >= 0:
    # Add import after FastAPI import
    lines.insert(import_idx + 1, "from fastapi.middleware.cors import CORSMiddleware\n")
    
    # Add middleware after app creation (adjust index since we inserted a line)
    middleware = '''
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
'''
    lines.insert(app_idx + 2, middleware)
    
    with open("$mainpy", "w") as f:
        f.writelines(lines)
    print("ok")
else:
    print("error")
    sys.exit(1)
PYTHON
    
    if [ $? -eq 0 ]; then
        echo "✅ $agent: CORS added"
    else
        echo "❌ $agent: Failed to add CORS"
        mv "$mainpy.backup" "$mainpy"
    fi
done

echo ""
echo "🔄 Restarting services..."
cd /opt/Dev-Tools/compose
docker compose restart

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 15

echo ""
echo "🏥 Health check..."
for port in 8001 8002 8003 8004 8005 8006; do
    status=$(curl -s http://localhost:$port/health 2>/dev/null || echo "error")
    echo "Port $port: $status"
done

echo ""
echo "✨ CORS configuration complete!"

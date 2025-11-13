#!/bin/bash
# Enable CORS on all Dev-Tools agents

echo "🔗 Adding CORS support to all agents..."

cd /opt/Dev-Tools

# Backup original files
for agent in orchestrator feature-dev code-review infrastructure cicd documentation; do
  cp agents/$agent/main.py agents/$agent/main.py.backup
done

# Add CORS to orchestrator
cat > /tmp/cors_patch.txt << 'EOF'
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://theshop.appsmithery.co",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
EOF

echo "✅ CORS configuration created"
echo "📝 Please manually add CORS middleware to each agent's main.py file"
echo ""
echo "Add this after 'from fastapi import FastAPI':"
cat /tmp/cors_patch.txt

echo ""
echo "Then restart services:"
echo "cd /opt/Dev-Tools/compose && docker compose restart"

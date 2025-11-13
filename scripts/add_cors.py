#!/usr/bin/env python3
"""Add CORS middleware to all Dev-Tools agents"""
import os
import sys

AGENTS = ["orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation"]
BASE_PATH = "/opt/Dev-Tools/agents"

CORS_IMPORT = "from fastapi.middleware.cors import CORSMiddleware\n"
CORS_MIDDLEWARE = '''
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
'''

def add_cors_to_agent(agent_name):
    """Add CORS to a single agent's main.py"""
    main_py = f"{BASE_PATH}/{agent_name}/main.py"
    
    if not os.path.exists(main_py):
        print(f"❌ {agent_name}: main.py not found")
        return False
    
    with open(main_py, 'r') as f:
        lines = f.readlines()
    
    # Check if already has CORS
    if any('CORSMiddleware' in line for line in lines):
        print(f"⏭️  {agent_name}: CORS already configured")
        return True
    
    # Backup
    with open(f"{main_py}.backup", 'w') as f:
        f.writelines(lines)
    
    # Find insertion points
    import_idx = None
    app_idx = None
    
    for i, line in enumerate(lines):
        if 'from fastapi import FastAPI' in line and import_idx is None:
            import_idx = i
        if line.strip().startswith('app = FastAPI') and app_idx is None:
            # Find the closing paren
            if ')' in line:
                app_idx = i
            else:
                for j in range(i + 1, len(lines)):
                    if ')' in lines[j]:
                        app_idx = j
                        break
    
    if import_idx is None or app_idx is None:
        print(f"❌ {agent_name}: Could not find FastAPI import or app initialization")
        return False
    
    # Insert CORS import after FastAPI import
    lines.insert(import_idx + 1, CORS_IMPORT)
    
    # Insert middleware after app initialization (adjust for inserted import line)
    lines.insert(app_idx + 2, CORS_MIDDLEWARE + '\n')
    
    # Write updated file
    with open(main_py, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ {agent_name}: CORS added")
    return True

def main():
    print("🔧 Adding CORS to all agents...\n")
    
    success_count = 0
    for agent in AGENTS:
        if add_cors_to_agent(agent):
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{len(AGENTS)} agents updated")
    
    if success_count == len(AGENTS):
        print("\n✨ CORS configuration complete!")
        print("🔄 Restart services with: cd /opt/Dev-Tools/compose && docker compose restart")
        return 0
    else:
        print("\n⚠️  Some agents failed to update")
        return 1

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Fix CORS middleware for orchestrator"""

with open("/opt/Dev-Tools/agents/orchestrator/main.py", "r") as f:
    lines = f.readlines()

# Check if middleware already added
if any("add_middleware" in line for line in lines):
    print("Middleware already present")
    exit(0)

# Find the app = FastAPI closing paren
app_line = None
for i, line in enumerate(lines):
    if line.strip().startswith("app = FastAPI("):
        # Find closing paren
        for j in range(i, min(i + 10, len(lines))):
            if ")" in lines[j]:
                app_line = j
                break
        break

if app_line is None:
    print("Could not find app initialization")
    exit(1)

# Insert middleware after app creation
middleware_code = """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

"""

lines.insert(app_line + 1, middleware_code)

with open("/opt/Dev-Tools/agents/orchestrator/main.py", "w") as f:
    f.writelines(lines)

print("✅ CORS middleware added to orchestrator")

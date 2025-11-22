#!/usr/bin/env python3
"""
Temporary script to add payload logging to main.py
"""

# Read the main.py file
with open("/opt/Dev-Tools/agent_orchestrator/main.py", "r") as f:
    content = f.read()

# Find the line where we process webhook
search_line = "    # Process webhook and get action"
if search_line in content:
    # Add logging before it
    new_code = """    # DEBUG: Log full event payload
    import json
    logger.info(f"🔍 WEBHOOK EVENT TYPE: {event.get('type')}.{event.get('action')}")
    logger.info(f"🔍 WEBHOOK DATA KEYS: {list(event.get('data', {}).keys())}")
    logger.info(f"🔍 WEBHOOK PAYLOAD: {json.dumps(event, indent=2, default=str)[:2000]}")
    
"""
    content = content.replace(search_line, new_code + search_line)

    # Write back
    with open("/opt/Dev-Tools/agent_orchestrator/main.py", "w") as f:
        f.write(content)

    print("✅ Added webhook payload logging to main.py")
else:
    print("❌ Could not find the target line in main.py")

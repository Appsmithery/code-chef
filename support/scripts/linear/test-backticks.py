#!/usr/bin/env python3
"""Test backtick file reference matching."""

import sys
from pathlib import Path

# Add shared to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))
sys.path.insert(0, str(repo_root / "shared" / "lib"))

from lib.github_permalink_generator import GitHubPermalinkGenerator

# Initialize generator
generator = GitHubPermalinkGenerator(
    "https://github.com/Appsmithery/Dev-Tools",
    str(repo_root)
)

# Test cases with backticks (like Linear comments)
test_cases = [
    "Configuration updated: `config/env/.env` (LINEAR_API_KEY set)",
    "Services restarted: `deploy/docker-compose.yml`",
    "Health checks passing: `agent_orchestrator/main.py lines 880-920`",
    "Check orchestrator startup in `deploy/docker-compose.yml` service definition.",
    "Implementation in `shared/lib/github_permalink_generator.py lines 45-120`",
    "See `support/scripts/linear/test-permalink-generation.py` for validation",
]

print("\n" + "=" * 70)
print("Backtick File Reference Test")
print("=" * 70)

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"  Input:  {test}")
    
    # Extract references
    refs = generator.extract_file_references(test)
    print(f"  Found:  {len(refs)} reference(s)")
    for ref in refs:
        print(f"    - {ref.path}", end="")
        if ref.line_start:
            if ref.line_end:
                print(f" lines {ref.line_start}-{ref.line_end}")
            else:
                print(f" line {ref.line_start}")
        else:
            print()
    
    # Enrich
    enriched = generator.enrich_markdown_with_permalinks(test)
    print(f"  Output: {enriched[:120]}...")
    
    # Check if enrichment happened
    if "[" in enriched and "](" in enriched:
        print("  Status: ✅ PASS - Permalink generated")
    else:
        print("  Status: ❌ FAIL - No permalink generated")

print("\n" + "=" * 70)

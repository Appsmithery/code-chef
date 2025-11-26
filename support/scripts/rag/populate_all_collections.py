#!/usr/bin/env python3
"""
RAG Collection Population Master Script
Runs all 4 indexing scripts in sequence via orchestrator container.
"""

import subprocess
import sys
from datetime import datetime

# Scripts to run (in order)
SCRIPTS = [
    ("code_patterns", "/app/support/scripts/rag/index_code_patterns.py"),
    ("feature_specs", "/app/support/scripts/rag/index_feature_specs.py"),
    ("issue_tracker", "/app/support/scripts/rag/index_issue_tracker.py"),
    ("task_context", "/app/support/scripts/rag/index_task_context.py"),
]

CONTAINER = "deploy-orchestrator-1"


def run_indexing_script(name: str, script_path: str) -> bool:
    """Run indexing script inside container"""
    print(f"\n{'=' * 70}")
    print(f"🚀 Running {name} indexing...")
    print(f"{'=' * 70}\n")
    
    try:
        result = subprocess.run(
            ["docker", "exec", CONTAINER, "python3", script_path],
            capture_output=False,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"\n✅ {name} indexing completed successfully")
            return True
        else:
            print(f"\n❌ {name} indexing failed with exit code {result.returncode}")
            return False
    
    except subprocess.TimeoutExpired:
        print(f"\n⏱️ {name} indexing timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"\n❌ {name} indexing error: {e}")
        return False


def main():
    """Run all indexing scripts"""
    print("=" * 70)
    print("📊 RAG Collection Population - Master Script")
    print(f"⏰ Started: {datetime.now().isoformat()}")
    print("=" * 70)
    
    results = {}
    
    for name, script_path in SCRIPTS:
        success = run_indexing_script(name, script_path)
        results[name] = success
    
    # Print summary
    print("\n" + "=" * 70)
    print("📋 Summary")
    print("=" * 70)
    
    for name, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {name}: {status}")
    
    total = len(results)
    successful = sum(1 for s in results.values() if s)
    
    print(f"\n🎯 Total: {successful}/{total} collections populated successfully")
    print(f"⏰ Finished: {datetime.now().isoformat()}")
    print("=" * 70)
    
    # Exit with error if any failed
    sys.exit(0 if successful == total else 1)


if __name__ == "__main__":
    main()

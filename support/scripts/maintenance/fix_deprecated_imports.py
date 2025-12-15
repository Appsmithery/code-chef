#!/usr/bin/env python3
"""Fix deprecated import paths across all Python files."""

import re
import pathlib
from typing import Dict, List, Tuple

# Mapping of deprecated → current import paths
IMPORT_MIGRATIONS = {
    r'from agents\._shared\.qdrant_client import': 'from shared.lib.qdrant_client import',
    r'from agents\._shared\.llm_providers import': 'from shared.lib.llm_providers import',
    r'from agents\._shared\.mcp_discovery import': 'from shared.lib.mcp_discovery import',
    r'from agents\._shared\.langgraph_base import': 'from shared.lib.langgraph_base import',
    r'from agents\.cicd\.service import': 'from agent_cicd.service import',
    r'from agents\.code_review\.service import': 'from agent_code-review.service import',
    r'from agents\.documentation\.service import': 'from agent_documentation.service import',
    r'from agents\.feature_dev\.service import': 'from agent_feature-dev.service import',
    r'from agents\.infrastructure\.service import': 'from agent_infrastructure.service import',
    r'from agents\.langgraph\.workflow import': 'from shared.services.langgraph.workflow import',
}

def fix_imports_in_file(file_path: pathlib.Path) -> Tuple[bool, int]:
    """
    Fix deprecated imports in a single file.
    
    Returns:
        Tuple of (was_modified, num_replacements)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False, 0
    
    original_content = content
    replacements = 0
    
    for old_pattern, new_pattern in IMPORT_MIGRATIONS.items():
        matches = re.findall(old_pattern, content)
        if matches:
            content = re.sub(old_pattern, new_pattern, content)
            replacements += len(matches)
    
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, replacements
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return False, 0
    
    return False, 0

def main():
    """Fix imports across all Python files."""
    print("🔧 Fixing deprecated imports across Python files...")
    
    base_path = pathlib.Path('.')
    files_modified = 0
    total_replacements = 0
    
    # Scan all Python files
    for py_file in base_path.rglob('*.py'):
        # Skip excluded directories
        if any(x in str(py_file) for x in ['_archive', 'venv', '__pycache__', 'node_modules', '.venv']):
            continue
        
        was_modified, replacements = fix_imports_in_file(py_file)
        
        if was_modified:
            files_modified += 1
            total_replacements += replacements
            print(f"✅ Fixed {replacements} import(s) in: {py_file}")
    
    print(f"\n✅ Import fix complete!")
    print(f"   Files modified: {files_modified}")
    print(f"   Total replacements: {total_replacements}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Analyze Python imports for deprecated path references."""

import ast
import pathlib
import json
from typing import Dict, List, Any

# Deprecated paths to detect
DEPRECATED_PATHS = [
    'agents/',
    'containers/',
    'compose/',
    'infrastructure/',
    'tmp/',
    'bin/',
    '_archive/'
]

def analyze_imports() -> Dict[str, Any]:
    """Scan all Python files for deprecated import patterns."""
    results = {
        'files_scanned': 0,
        'violations': [],
        'summary': {}
    }
    
    base_path = pathlib.Path('.')
    
    for py_file in base_path.rglob('*.py'):
        # Skip excluded directories
        if any(x in str(py_file) for x in ['_archive', 'venv', '__pycache__', 'node_modules']):
            continue
        
        results['files_scanned'] += 1
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(py_file))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_path = node.module.replace('.', '/')
                        if any(dep in module_path for dep in DEPRECATED_PATHS):
                            results['violations'].append({
                                'file': str(py_file),
                                'line': node.lineno,
                                'type': 'from_import',
                                'module': node.module,
                                'names': [alias.name for alias in node.names]
                            })
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module_path = alias.name.replace('.', '/')
                        if any(dep in module_path for dep in DEPRECATED_PATHS):
                            results['violations'].append({
                                'file': str(py_file),
                                'line': node.lineno,
                                'type': 'import',
                                'module': alias.name,
                                'names': [alias.name]
                            })
        
        except Exception as e:
            results['violations'].append({
                'file': str(py_file),
                'line': 0,
                'type': 'parse_error',
                'module': str(e),
                'names': []
            })
    
    # Generate summary
    results['summary'] = {
        'total_violations': len(results['violations']),
        'files_with_violations': len(set(v['file'] for v in results['violations'])),
        'violation_types': {}
    }
    
    for violation in results['violations']:
        vtype = violation['type']
        results['summary']['violation_types'][vtype] = \
            results['summary']['violation_types'].get(vtype, 0) + 1
    
    return results

if __name__ == '__main__':
    print("🔍 Analyzing Python imports for deprecated paths...")
    results = analyze_imports()
    
    output_path = pathlib.Path('support/reports/import-violations.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Analysis complete!")
    print(f"   Files scanned: {results['files_scanned']}")
    print(f"   Total violations: {results['summary']['total_violations']}")
    print(f"   Files with violations: {results['summary']['files_with_violations']}")
    print(f"   Report saved to: {output_path}")
    
    if results['violations']:
        print("\n⚠️  Top violations:")
        for violation in results['violations'][:10]:
            print(f"   {violation['file']}:{violation['line']} - {violation['module']}")

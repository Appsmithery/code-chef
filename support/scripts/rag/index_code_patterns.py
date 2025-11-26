#!/usr/bin/env python3
"""
Index Code Patterns to Qdrant
Extracts Python code patterns from agent_orchestrator/ and indexes to code_patterns collection.
Useful for agents to learn from existing patterns and implementations.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import ast
import httpx

# Add repo root to path - Handle both container and host execution
if os.path.exists("/app/agent_orchestrator"):
    # Running in Docker container
    REPO_ROOT = Path("/app")
else:
    # Running on host
    SCRIPT_DIR = Path(__file__).resolve().parent
    REPO_ROOT = SCRIPT_DIR.parent.parent.parent

sys.path.insert(0, str(REPO_ROOT))

# Configuration
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8007")
COLLECTION_NAME = "code_patterns"

# Directories to index
CODE_DIRS = [
    REPO_ROOT / "agent_orchestrator" / "agents",
    REPO_ROOT / "agent_orchestrator" / "workflows",
    REPO_ROOT / "shared" / "lib",
]


def extract_python_patterns(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract meaningful code patterns from Python file.
    Patterns include: classes, functions, docstrings, imports, decorators
    """
    patterns = []

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))

        # Extract imports for dependency tracking
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        # Extract classes and functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                pattern = extract_code_entity(node, file_path, content, imports)
                if pattern:
                    patterns.append(pattern)

    except SyntaxError as e:
        print(f"  ⚠️ Syntax error in {file_path.relative_to(REPO_ROOT)}: {e}")
    except Exception as e:
        print(f"  ⚠️ Error parsing {file_path.relative_to(REPO_ROOT)}: {e}")

    return patterns


def extract_code_entity(
    node: ast.AST, file_path: Path, full_content: str, imports: List[str]
) -> Dict[str, Any]:
    """Extract a class or function as a code pattern"""
    entity_type = "class" if isinstance(node, ast.ClassDef) else "function"
    entity_name = node.name

    # Extract docstring
    docstring = ast.get_docstring(node) or ""

    # Extract decorators
    decorators = []
    for decorator in getattr(node, "decorator_list", []):
        if isinstance(decorator, ast.Name):
            decorators.append(decorator.id)
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            decorators.append(decorator.func.id)

    # Extract source code
    try:
        source_lines = full_content.split("\n")
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 20
        source_code = "\n".join(source_lines[start_line:end_line])
    except Exception:
        source_code = ""

    # Build searchable content
    content_parts = [
        f"{entity_type.capitalize()}: {entity_name}",
        f"File: {file_path.relative_to(REPO_ROOT)}",
    ]

    if docstring:
        content_parts.append(f"Documentation: {docstring}")

    if decorators:
        content_parts.append(f"Decorators: {', '.join(decorators)}")

    if imports:
        content_parts.append(
            f"Dependencies: {', '.join(imports[:10])}"
        )  # First 10 imports

    # Add abbreviated source code (first 500 chars)
    if source_code:
        abbreviated_source = source_code[:500] + (
            "..." if len(source_code) > 500 else ""
        )
        content_parts.append(f"Source:\n{abbreviated_source}")

    return {
        "content": "\n\n".join(content_parts),
        "entity_type": entity_type,
        "entity_name": entity_name,
        "file_path": str(file_path.relative_to(REPO_ROOT)),
        "file_name": file_path.name,
        "directory": str(file_path.parent.relative_to(REPO_ROOT)),
        "docstring": docstring,
        "decorators": decorators,
        "imports": imports[:20],  # Limit to 20 most relevant
        "line_number": node.lineno,
        "source_code": source_code[:2000],  # Limit source to 2000 chars
        "language": "python",
        "pattern_type": determine_pattern_type(entity_name, docstring, decorators),
    }


def determine_pattern_type(name: str, docstring: str, decorators: List[str]) -> str:
    """Classify the pattern type based on naming and decorators"""
    name_lower = name.lower()
    doc_lower = docstring.lower()

    # Check decorators first (highest confidence)
    if "app.post" in decorators or "app.get" in decorators or "app.put" in decorators:
        return "api_endpoint"
    if "staticmethod" in decorators or "classmethod" in decorators:
        return "utility_method"
    if "property" in decorators:
        return "property_accessor"

    # Check naming patterns
    if name_lower.startswith("test_"):
        return "test_case"
    if name.endswith("Agent") or name.endswith("Client"):
        return "agent_class"
    if name.endswith("Engine") or name.endswith("Manager"):
        return "orchestration_class"
    if name.endswith("Workflow"):
        return "workflow_definition"
    if "BaseModel" in docstring or "pydantic" in doc_lower:
        return "data_model"

    # Check function patterns
    if name_lower.startswith("get_") or name_lower.startswith("fetch_"):
        return "data_retrieval"
    if name_lower.startswith("create_") or name_lower.startswith("init_"):
        return "factory_pattern"
    if name_lower.startswith("process_") or name_lower.startswith("execute_"):
        return "business_logic"
    if name_lower.startswith("_") and not name_lower.startswith("__"):
        return "private_helper"

    # Default based on docstring hints
    if "workflow" in doc_lower or "orchestrat" in doc_lower:
        return "workflow_component"
    if "llm" in doc_lower or "model" in doc_lower or "gradient" in doc_lower:
        return "llm_integration"
    if "mcp" in doc_lower or "tool" in doc_lower:
        return "mcp_integration"

    return "general_pattern"


def collect_python_files(directories: List[Path]) -> List[Path]:
    """Recursively collect all Python files from directories"""
    python_files = []

    for directory in directories:
        if not directory.exists():
            print(f"⚠️ Directory not found: {directory}")
            continue

        for py_file in directory.rglob("*.py"):
            # Skip __pycache__, tests, and virtual environments
            if (
                "__pycache__" in str(py_file)
                or "venv" in str(py_file)
                or ".venv" in str(py_file)
            ):
                continue
            if py_file.name.startswith("test_"):
                continue  # Skip test files for now

            python_files.append(py_file)

    return python_files


async def index_to_rag_service(patterns: List[Dict[str, Any]]):
    """Index patterns to RAG service"""
    if not patterns:
        print("No patterns to index")
        return

    print(f"\n📤 Indexing {len(patterns)} patterns to RAG service...")

    # Prepare documents and metadata
    documents = [p["content"] for p in patterns]
    metadatas = [
        {
            "entity_type": p["entity_type"],
            "entity_name": p["entity_name"],
            "file_path": p["file_path"],
            "file_name": p["file_name"],
            "directory": p["directory"],
            "pattern_type": p["pattern_type"],
            "line_number": p["line_number"],
            "language": p["language"],
            "has_docstring": bool(p["docstring"]),
            "decorator_count": len(p["decorators"]),
        }
        for p in patterns
    ]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/index",
                json={
                    "documents": documents,
                    "metadatas": metadatas,
                    "collection": COLLECTION_NAME,
                },
            )
            response.raise_for_status()
            result = response.json()

            print(f"✅ Successfully indexed {result['indexed_count']} patterns")
            print(f"   Collection: {result['collection']}")
            return result

    except httpx.HTTPError as e:
        print(f"❌ HTTP error during indexing: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")
        raise
    except Exception as e:
        print(f"❌ Error indexing patterns: {e}")
        raise


async def main():
    """Main indexing workflow"""
    print("=" * 70)
    print("🔍 Code Pattern Indexing - Agent Learning System")
    print("=" * 70)

    print(f"\n📂 Scanning directories:")
    for dir_path in CODE_DIRS:
        print(f"   - {dir_path.relative_to(REPO_ROOT)}")

    # Collect Python files
    python_files = collect_python_files(CODE_DIRS)
    print(f"\n📝 Found {len(python_files)} Python files")

    # Extract patterns
    all_patterns = []
    print("\n🔬 Extracting code patterns...")

    for py_file in python_files:
        patterns = extract_python_patterns(py_file)
        if patterns:
            print(f"  ✓ {py_file.relative_to(REPO_ROOT)}: {len(patterns)} patterns")
            all_patterns.extend(patterns)

    print(f"\n✅ Extracted {len(all_patterns)} total patterns")

    # Show pattern type distribution
    pattern_types = {}
    for pattern in all_patterns:
        pt = pattern["pattern_type"]
        pattern_types[pt] = pattern_types.get(pt, 0) + 1

    print("\n📊 Pattern Type Distribution:")
    for pt, count in sorted(pattern_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {pt}: {count}")

    # Index to RAG service
    if all_patterns:
        await index_to_rag_service(all_patterns)

    print("\n" + "=" * 70)
    print("✅ Code Pattern Indexing Complete!")
    print("=" * 70)
    print(f"\n💡 Query examples:")
    print(f"   curl -X POST {RAG_SERVICE_URL}/query \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(
        f'     -d \'{{"query": "workflow execution patterns", "collection": "{COLLECTION_NAME}"}}\''
    )


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Test GitHub Permalink Generator

Usage:
    python test_permalink_generator.py
"""

import sys
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent / "shared" / "lib"))

from github_permalink_generator import (
    init_permalink_generator,
    generate_permalink,
    enrich_description_with_permalinks,
    extract_file_references,
)


def test_basic_permalink():
    """Test basic permalink generation"""
    print("\n🧪 Test 1: Basic Permalink Generation")
    print("-" * 50)

    url = generate_permalink("agent_orchestrator/main.py")
    print(f"✅ File permalink: {url}")
    assert "/blob/" in url
    assert "agent_orchestrator/main.py" in url


def test_line_range_permalink():
    """Test permalink with line range"""
    print("\n🧪 Test 2: Line Range Permalink")
    print("-" * 50)

    url = generate_permalink("agent_orchestrator/main.py", 45, 67)
    print(f"✅ Line range permalink: {url}")
    assert "#L45-L67" in url


def test_single_line_permalink():
    """Test permalink with single line"""
    print("\n🧪 Test 3: Single Line Permalink")
    print("-" * 50)

    url = generate_permalink("shared/lib/mcp_client.py", 100)
    print(f"✅ Single line permalink: {url}")
    assert "#L100" in url


def test_extract_file_references():
    """Test file reference extraction"""
    print("\n🧪 Test 4: Extract File References")
    print("-" * 50)

    text = """
    Review the changes in agent_orchestrator/main.py lines 45-67 and 
    check shared/lib/mcp_client.py line 100. Also update config/env/.env.template.
    """

    refs = extract_file_references(text)
    print(f"✅ Extracted {len(refs)} references:")
    for ref in refs:
        print(f"   - {ref.path}", end="")
        if ref.line_start:
            if ref.line_end:
                print(f" (L{ref.line_start}-L{ref.line_end})")
            else:
                print(f" (L{ref.line_start})")
        else:
            print()

    assert len(refs) >= 3


def test_enrich_description():
    """Test description enrichment"""
    print("\n🧪 Test 5: Enrich Description with Permalinks")
    print("-" * 50)

    description = "Review agent_orchestrator/main.py lines 45-67"
    enriched = enrich_description_with_permalinks(description)

    print(f"Original: {description}")
    print(f"Enriched: {enriched}")

    assert "[agent_orchestrator/main.py (L45-L67)]" in enriched
    assert "](https://github.com/" in enriched
    print("✅ Description enriched successfully")


def test_multiple_references():
    """Test multiple file references in one description"""
    print("\n🧪 Test 6: Multiple File References")
    print("-" * 50)

    description = """
    Implement JWT authentication:
    1. Update agent_orchestrator/main.py lines 45-67
    2. Review shared/lib/auth.py line 23
    3. Configure config/env/.env.template
    """

    enriched = enrich_description_with_permalinks(description)

    print("Enriched description:")
    print(enriched)
    print()

    # Count permalink occurrences
    permalink_count = enriched.count("](https://github.com/")
    print(f"✅ Found {permalink_count} permalinks")
    assert permalink_count >= 3


def main():
    """Run all tests"""
    print("=" * 60)
    print("GitHub Permalink Generator Tests")
    print("=" * 60)

    # Initialize generator
    print("\n🔧 Initializing permalink generator...")
    init_permalink_generator("https://github.com/Appsmithery/Dev-Tools")
    print("✅ Initialized")

    try:
        test_basic_permalink()
        test_line_range_permalink()
        test_single_line_permalink()
        test_extract_file_references()
        test_enrich_description()
        test_multiple_references()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test script for multi-layer Linear configuration.

This script verifies:
1. YAML config loads correctly
2. .env secrets are merged
3. Environment overrides work
4. Config methods return expected values
5. Type validation works

Usage:
    python support/scripts/linear/test-linear-config.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add shared/lib to Python path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))

# Load .env file
env_path = repo_root / "config" / "env" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
else:
    print(f"WARNING: .env file not found at {env_path}")

from lib.linear_config import get_linear_config, LinearConfig


def test_config_loading():
    """Test basic config loading"""
    print("=" * 80)
    print("TEST 1: Basic Configuration Loading")
    print("=" * 80)

    try:
        config = get_linear_config()
        print("✓ Config loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False


def test_structural_config():
    """Test structural config from YAML"""
    print("\n" + "=" * 80)
    print("TEST 2: Structural Configuration (YAML)")
    print("=" * 80)

    try:
        config = get_linear_config()

        # Workspace
        print(f"\nWorkspace:")
        print(f"  Slug: {config.workspace.slug}")
        print(f"  Team ID: {config.workspace.team_id}")
        assert config.workspace.slug == "dev-ops"
        assert config.workspace.team_id == "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
        print("  ✓ Workspace config correct")

        # Approval hub
        print(f"\nApproval Hub:")
        print(f"  Issue ID: {config.approval_hub.issue_id}")
        assert config.approval_hub.issue_id == "DEV-68"
        print("  ✓ Approval hub config correct")

        # Templates
        print(f"\nTemplates:")
        print(f"  HITL Orchestrator: {config.templates['hitl_orchestrator'].uuid}")
        print(f"  Task Orchestrator: {config.templates['task_orchestrator'].uuid}")
        assert (
            config.templates["hitl_orchestrator"].uuid
            == "aa632a46-ea22-4dd0-9403-90b0d1f05aa0"
        )
        assert (
            config.templates["task_orchestrator"].uuid
            == "e9591ca7-c9cf-4960-acce-a99792542b95"
        )
        print("  ✓ Template config correct")

        # Custom fields
        print(f"\nCustom Fields:")
        print(f"  Required Action ID: {config.custom_fields['required_action'].id}")
        print(f"  Request Status ID: {config.custom_fields['request_status'].id}")
        assert (
            config.custom_fields["required_action"].id
            == "ac2c5d12-ead1-4444-af32-62e9bcacee72"
        )
        assert (
            config.custom_fields["request_status"].id
            == "ee8b5f23-a3c6-41e2-938c-7f8161d50de7"
        )
        print("  ✓ Custom fields config correct")

        # Labels
        print(f"\nLabels:")
        print(f"  HITL: {config.labels.hitl}")
        print(f"  Orchestrator: {config.labels.orchestrator}")
        assert config.labels.hitl == "f6157a00-f2d8-4417-a927-ba832733da90"
        assert config.labels.orchestrator == "0bc7a4c8-ece0-4778-9f21-eac54a7c469b"
        print("  ✓ Labels config correct")

        # Default assignee
        print(f"\nDefault Assignee:")
        print(f"  ID: {config.default_assignee.id}")
        print(f"  Email: {config.default_assignee.email}")
        assert config.default_assignee.id == "12b01869-730b-4898-9ca3-88c463764071"
        assert config.default_assignee.email == "alex@appsmithery.co"
        print("  ✓ Default assignee config correct")

        print("\n✓ All structural config tests passed")
        return True

    except AssertionError as e:
        print(f"\n✗ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False


def test_secrets_loading():
    """Test secrets loading from .env"""
    print("\n" + "=" * 80)
    print("TEST 3: Secrets Loading (.env)")
    print("=" * 80)

    try:
        config = get_linear_config()

        print(f"\nAPI Key: {config.api_key[:20]}..." if config.api_key else "Not set")
        print(
            f"OAuth Client ID: {config.oauth_client_id[:10]}..."
            if config.oauth_client_id
            else "Not set"
        )
        print(
            f"OAuth Client Secret: {'***' if config.oauth_client_secret else 'Not set'}"
        )
        print(
            f"Webhook Secret: {'***' if config.webhook_signing_secret else 'Not set'}"
        )

        if not config.api_key:
            print("\n⚠ WARNING: LINEAR_API_KEY not set in .env")
            return False

        print("\n✓ Secrets loaded successfully")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False


def test_config_methods():
    """Test config helper methods"""
    print("\n" + "=" * 80)
    print("TEST 4: Configuration Methods")
    print("=" * 80)

    try:
        config = get_linear_config()

        # Test get_template_uuid with fallback
        print("\nTesting get_template_uuid()...")
        orchestrator_uuid = config.get_template_uuid("orchestrator", scope="workspace")
        print(f"  Orchestrator HITL template: {orchestrator_uuid}")
        assert orchestrator_uuid == "aa632a46-ea22-4dd0-9403-90b0d1f05aa0"

        feature_dev_uuid = config.get_template_uuid("feature-dev", scope="workspace")
        print(f"  Feature-dev HITL template (fallback): {feature_dev_uuid}")
        assert (
            feature_dev_uuid == "aa632a46-ea22-4dd0-9403-90b0d1f05aa0"
        )  # Should fallback to orchestrator
        print("  ✓ Template UUID lookup works")

        # Test get_approval_policy
        print("\nTesting get_approval_policy()...")
        high_policy = config.get_approval_policy("high")
        print(f"  High risk policy:")
        print(f"    Priority: {high_policy.priority}")
        print(f"    Required actions: {high_policy.required_actions}")
        assert high_policy.priority == 1
        assert "Review proposed changes" in high_policy.required_actions
        assert "Verify risks are acceptable" in high_policy.required_actions
        print("  ✓ Approval policy lookup works")

        # Test get_custom_field_id
        print("\nTesting get_custom_field_id()...")
        required_action_id = config.get_custom_field_id("required_action")
        print(f"  Required action field ID: {required_action_id}")
        assert required_action_id == "ac2c5d12-ead1-4444-af32-62e9bcacee72"
        print("  ✓ Custom field ID lookup works")

        print("\n✓ All method tests passed")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_environment_overrides():
    """Test environment variable overrides"""
    print("\n" + "=" * 80)
    print("TEST 5: Environment Variable Overrides")
    print("=" * 80)

    try:
        # Test override for agent-specific template (supported via env vars)
        print("\nTesting agent-specific template override...")
        original_template = os.getenv("HITL_FEATURE_DEV_TEMPLATE_UUID")
        test_uuid = "test-uuid-12345"
        os.environ["HITL_FEATURE_DEV_TEMPLATE_UUID"] = test_uuid

        # Get template UUID with override
        config = get_linear_config(reload=True)
        feature_dev_uuid = config.get_template_uuid("feature_dev", scope="workspace")
        print(f"Feature-dev template after override: {feature_dev_uuid}")
        assert feature_dev_uuid == test_uuid
        print("✓ Environment override works for agent-specific templates")

        # Restore original
        if original_template:
            os.environ["HITL_FEATURE_DEV_TEMPLATE_UUID"] = original_template
        else:
            del os.environ["HITL_FEATURE_DEV_TEMPLATE_UUID"]

        # Reload config and verify fallback
        config = get_linear_config(reload=True)
        feature_dev_uuid = config.get_template_uuid("feature_dev", scope="workspace")
        print(f"Feature-dev template after restore (fallback): {feature_dev_uuid}")
        assert (
            feature_dev_uuid == "aa632a46-ea22-4dd0-9403-90b0d1f05aa0"
        )  # Should fallback to orchestrator
        print("✓ Template fallback works after override removal")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("LINEAR CONFIGURATION TEST SUITE")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("Config Loading", test_config_loading()))
    results.append(("Structural Config", test_structural_config()))
    results.append(("Secrets Loading", test_secrets_loading()))
    results.append(("Config Methods", test_config_methods()))
    results.append(("Environment Overrides", test_environment_overrides()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<50} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

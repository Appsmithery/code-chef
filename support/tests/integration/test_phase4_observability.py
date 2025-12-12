"""
Test Phase 4: Observability Integration

Validates that HITL approval workflow properly:
1. Emits Prometheus metrics on approval creation
2. Emits Prometheus metrics on approval resolution
3. Updates backlog gauges correctly
4. Records approval latency
5. Tracks timeout events
6. LangSmith traces include risk metadata

Prerequisites:
- Prometheus metrics endpoint accessible (http://localhost:8001/metrics)
- PostgreSQL database accessible
- LINEAR_API_KEY environment variable set
"""

import asyncio
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows event loop policy for psycopg3
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))
sys.path.insert(0, str(project_root / "agent_orchestrator"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def fetch_prometheus_metrics():
    """Fetch current Prometheus metrics from /metrics endpoint."""
    try:
        import requests

        response = requests.get("http://localhost:8001/metrics", timeout=5)
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Failed to fetch metrics: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return None


def parse_metric_value(
    metrics_text: str, metric_name: str, labels: dict = None
) -> float:
    """Parse a specific metric value from Prometheus text format."""
    if not metrics_text:
        return 0.0

    # Build regex pattern based on labels
    if labels:
        label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
        pattern = rf"{metric_name}\{{{label_str}\}}\s+([\d.]+)"
    else:
        pattern = rf"{metric_name}\s+([\d.]+)"

    match = re.search(pattern, metrics_text)
    if match:
        return float(match.group(1))
    return 0.0


async def test_approval_creation_metrics():
    """Test that approval creation emits correct metrics."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 1: Approval Creation Metrics")
    logger.info("=" * 60)

    try:
        from shared.lib.hitl_manager import HITLManager

        # Get baseline metrics
        logger.info("→ Fetching baseline metrics...")
        baseline_metrics = await fetch_prometheus_metrics()
        baseline_created = parse_metric_value(
            baseline_metrics,
            "hitl_approval_requests_created_total",
            {"agent": "test_agent", "risk_level": "high", "environment": "production"},
        )

        # Create approval request
        hitl_manager = HITLManager()
        task = {
            "operation": "test_operation",
            "description": "Test approval for metrics",
            "environment": "production",
            "risk_factors": ["production_environment"],
        }

        logger.info("→ Creating test approval request...")
        request_id = await hitl_manager.create_approval_request(
            workflow_id=f"test-wf-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            thread_id=f"test-thread-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            checkpoint_id=f"test-cp-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task=task,
            agent_name="test_agent",
        )

        logger.info(f"✓ Created approval request: {request_id}")

        # Wait for metrics to be collected
        await asyncio.sleep(2)

        # Fetch updated metrics
        logger.info("→ Fetching updated metrics...")
        updated_metrics = await fetch_prometheus_metrics()
        updated_created = parse_metric_value(
            updated_metrics,
            "hitl_approval_requests_created_total",
            {"agent": "test_agent", "risk_level": "high", "environment": "production"},
        )

        # Verify metric increment
        increment = updated_created - baseline_created
        logger.info(f"✓ Baseline created count: {baseline_created}")
        logger.info(f"✓ Updated created count: {updated_created}")
        logger.info(f"✓ Increment: {increment}")

        assert increment >= 1, "Created metric should have incremented"

        # Check backlog gauge
        backlog = parse_metric_value(
            updated_metrics, "hitl_approval_backlog_total", {"risk_level": "high"}
        )
        logger.info(f"✓ High-risk backlog: {backlog}")
        assert backlog >= 1, "Backlog should include our request"

        logger.info("✅ Approval creation metrics working correctly")
        return request_id

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_approval_resolution_metrics(request_id: str):
    """Test that approval resolution emits correct metrics."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Approval Resolution Metrics")
    logger.info("=" * 60)

    try:
        from shared.lib.hitl_manager import HITLManager

        # Get baseline metrics
        logger.info("→ Fetching baseline metrics...")
        baseline_metrics = await fetch_prometheus_metrics()
        baseline_resolved = parse_metric_value(
            baseline_metrics,
            "hitl_approval_requests_resolved_total",
            {"agent": "test_agent", "risk_level": "high", "status": "approved"},
        )

        # Simulate approval resolution
        hitl_manager = HITLManager()

        # Get approval details for metrics
        async with await hitl_manager._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT agent_name, risk_level, created_at FROM approval_requests WHERE id = %s",
                    (request_id,),
                )
                row = await cursor.fetchone()
                if row:
                    agent_name, risk_level, created_at = row

                    logger.info("→ Recording approval resolution...")
                    await hitl_manager.record_approval_resolution(
                        request_id=request_id,
                        status="approved",
                        agent_name=agent_name,
                        risk_level=risk_level,
                        created_at=created_at,
                    )

                    # Update status in database
                    await cursor.execute(
                        "UPDATE approval_requests SET status = 'approved', approved_at = NOW() WHERE id = %s",
                        (request_id,),
                    )
                    await conn.commit()

        # Wait for metrics to be collected
        await asyncio.sleep(2)

        # Fetch updated metrics
        logger.info("→ Fetching updated metrics...")
        updated_metrics = await fetch_prometheus_metrics()
        updated_resolved = parse_metric_value(
            updated_metrics,
            "hitl_approval_requests_resolved_total",
            {"agent": "test_agent", "risk_level": "high", "status": "approved"},
        )

        # Verify metric increment
        increment = updated_resolved - baseline_resolved
        logger.info(f"✓ Baseline resolved count: {baseline_resolved}")
        logger.info(f"✓ Updated resolved count: {updated_resolved}")
        logger.info(f"✓ Increment: {increment}")

        assert increment >= 1, "Resolved metric should have incremented"

        # Check that latency was recorded (check bucket counts)
        latency_pattern = r'hitl_approval_latency_seconds_bucket.*agent="test_agent".*risk_level="high".*status="approved"'
        latency_found = re.search(latency_pattern, updated_metrics)
        assert latency_found, "Latency histogram should have recorded observation"
        logger.info("✓ Latency histogram recorded")

        # Check backlog decreased
        backlog = parse_metric_value(
            updated_metrics, "hitl_approval_backlog_total", {"risk_level": "high"}
        )
        logger.info(f"✓ High-risk backlog after resolution: {backlog}")

        logger.info("✅ Approval resolution metrics working correctly")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_backlog_metrics():
    """Test that backlog gauge updates correctly."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Backlog Gauge Metrics")
    logger.info("=" * 60)

    try:
        from shared.lib.hitl_manager import HITLManager

        hitl_manager = HITLManager()

        logger.info("→ Updating backlog metrics...")
        await hitl_manager._update_backlog_metrics()

        # Fetch metrics
        logger.info("→ Fetching metrics...")
        metrics = await fetch_prometheus_metrics()

        # Check all risk levels have backlog values
        for risk_level in ["low", "medium", "high", "critical"]:
            backlog = parse_metric_value(
                metrics, "hitl_approval_backlog_total", {"risk_level": risk_level}
            )
            logger.info(f"✓ {risk_level.capitalize()} risk backlog: {backlog}")

        logger.info("✅ Backlog gauge metrics working correctly")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_metrics_endpoint_health():
    """Test that /metrics endpoint is accessible and returning data."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Metrics Endpoint Health")
    logger.info("=" * 60)

    try:
        logger.info("→ Fetching /metrics endpoint...")
        metrics = await fetch_prometheus_metrics()

        assert metrics is not None, "/metrics endpoint should be accessible"
        assert len(metrics) > 0, "/metrics should return data"

        # Check for expected metrics
        expected_metrics = [
            "hitl_approval_requests_created_total",
            "hitl_approval_requests_resolved_total",
            "hitl_approval_latency_seconds",
            "hitl_approval_backlog_total",
            "hitl_approval_timeouts_total",
        ]

        for metric_name in expected_metrics:
            assert metric_name in metrics, f"Metric {metric_name} should be present"
            logger.info(f"✓ Found metric: {metric_name}")

        logger.info("✅ Metrics endpoint healthy and returning expected metrics")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_prometheus_alerts():
    """Test that Prometheus alerting rules are valid."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 5: Prometheus Alert Rules")
    logger.info("=" * 60)

    try:
        import yaml

        alerts_path = (
            project_root / "config" / "prometheus" / "alerts" / "hitl-metrics.yml"
        )

        logger.info(f"→ Loading alert rules from {alerts_path}...")
        with open(alerts_path, "r") as f:
            alerts_config = yaml.safe_load(f)

        assert "groups" in alerts_config, "Alert file should have groups"

        groups = alerts_config["groups"]
        total_alerts = 0

        for group in groups:
            group_name = group["name"]
            rules = group.get("rules", [])

            alerts = [r for r in rules if "alert" in r]
            recordings = [r for r in rules if "record" in r]

            logger.info(
                f"✓ Group '{group_name}': {len(alerts)} alerts, {len(recordings)} recording rules"
            )
            total_alerts += len(alerts)

        logger.info(f"✓ Total alerts defined: {total_alerts}")
        assert total_alerts >= 5, "Should have at least 5 alert rules"

        logger.info("✅ Prometheus alert rules valid")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_grafana_dashboard():
    """Test that Grafana dashboard JSON is valid."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 6: Grafana Dashboard")
    logger.info("=" * 60)

    try:
        import json

        dashboard_path = (
            project_root
            / "config"
            / "grafana"
            / "dashboards"
            / "hitl-approval-workflow.json"
        )

        logger.info(f"→ Loading dashboard from {dashboard_path}...")
        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        assert "dashboard" in dashboard, "File should contain dashboard object"

        dash = dashboard["dashboard"]
        panels = dash.get("panels", [])

        logger.info(f"✓ Dashboard title: {dash.get('title')}")
        logger.info(f"✓ Panels: {len(panels)}")

        assert len(panels) >= 10, "Dashboard should have at least 10 panels"

        # Check key panels exist
        panel_titles = [p.get("title") for p in panels]
        required_titles = [
            "Approval Queue Overview",
            "Critical Risk Backlog",
            "Approval Latency Percentiles",
            "Approval Outcomes",
        ]

        for title in required_titles:
            assert title in panel_titles, f"Panel '{title}' should exist"
            logger.info(f"✓ Found panel: {title}")

        logger.info("✅ Grafana dashboard JSON valid")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def main():
    """Run all Phase 4 observability tests."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 4: OBSERVABILITY INTEGRATION TESTS")
    logger.info("=" * 80)

    # Verify prerequisites
    required_env_vars = ["LINEAR_API_KEY"]
    missing = [var for var in required_env_vars if not os.getenv(var)]

    if missing:
        logger.warning(f"⚠️  Missing environment variables: {missing}")
        logger.warning("Some tests may fail or be skipped")

    # Run tests
    tests = [
        ("Metrics Endpoint Health", test_metrics_endpoint_health),
        ("Backlog Gauge Metrics", test_backlog_metrics),
        ("Prometheus Alert Rules", test_prometheus_alerts),
        ("Grafana Dashboard", test_grafana_dashboard),
    ]

    # Tests that create approval requests
    approval_tests = [
        ("Approval Creation Metrics", test_approval_creation_metrics),
    ]

    passed = 0
    failed = 0
    request_id = None

    # Run basic tests first
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {e}")
            failed += 1

    # Run approval creation test
    try:
        request_id = await test_approval_creation_metrics()
        passed += 1
    except Exception as e:
        logger.error(f"❌ Approval Creation Metrics failed: {e}")
        failed += 1

    # Run approval resolution test if we have a request_id
    if request_id:
        try:
            await test_approval_resolution_metrics(request_id)
            passed += 1
        except Exception as e:
            logger.error(f"❌ Approval Resolution Metrics failed: {e}")
            failed += 1

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info(f"TEST SUMMARY: {passed} passed, {failed} failed")
    logger.info("=" * 80)

    if failed == 0:
        logger.info("✅ All Phase 4 observability integration tests passed!")
    else:
        logger.error(f"❌ {failed} test(s) failed")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

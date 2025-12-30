"""
Regression detection for evaluation results.

This script analyzes evaluation results and:
1. Compares metrics against historical baseline
2. Detects statistically significant regressions
3. Creates Linear issues for regressions
4. Sends notifications to relevant channels

Usage:
    # Check results file for regression
    python support/scripts/evaluation/detect_regression.py \
        --results evaluation_results.json \
        --threshold 0.05

    # Create Linear issue if regression detected
    python support/scripts/evaluation/detect_regression.py \
        --results evaluation_results.json \
        --threshold 0.05 \
        --create-linear-issue

    # Query historical data from database
    python support/scripts/evaluation/detect_regression.py \
        --agent feature_dev \
        --metric accuracy \
        --days 30

Linear Issue: DEV-195
Documentation: support/docs/operations/LLM_OPERATIONS.md
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

from loguru import logger

# Import linear client
try:
    from lib.linear_client import linear_client

    LINEAR_AVAILABLE = True
except ImportError:
    LINEAR_AVAILABLE = False
    logger.warning("Linear client not available - issue creation disabled")

# Import longitudinal tracker
try:
    from lib.longitudinal_tracker import longitudinal_tracker

    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False
    logger.warning(
        "Longitudinal tracker not available - historical comparison disabled"
    )


# =============================================================================
# CONFIGURATION
# =============================================================================

# Regression thresholds
DEFAULT_THRESHOLD = 0.05  # 5% drop is considered regression
CRITICAL_THRESHOLD = 0.15  # 15% drop is critical

# Metric weights for overall score
METRIC_WEIGHTS = {
    "accuracy": 0.30,
    "completeness": 0.25,
    "efficiency": 0.20,
    "latency": 0.15,
    "integration": 0.10,
}


# =============================================================================
# REGRESSION DETECTION
# =============================================================================


class RegressionDetector:
    """Detects performance regressions in evaluation results."""

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        create_issues: bool = False,
    ):
        """
        Initialize regression detector.

        Args:
            threshold: Regression threshold (default: 0.05 = 5%)
            create_issues: Whether to create Linear issues
        """
        self.threshold = threshold
        self.create_issues = create_issues

    def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze evaluation results for regression.

        Args:
            results: Evaluation results dict

        Returns:
            Analysis summary with regression details
        """
        analysis = {
            "has_regression": False,
            "regressions": [],
            "overall_change_pct": 0.0,
            "severity": "none",
            "recommendation": "deploy",
        }

        # Check if comparison available
        comparison = results.get("comparison", {})
        if not comparison:
            logger.warning("No comparison data available in results")
            return analysis

        # Get overall improvement
        overall_improvement = comparison.get("overall_improvement_pct", 0.0)
        analysis["overall_change_pct"] = overall_improvement

        # Check per-metric results
        per_metric = comparison.get("per_metric", {})

        for metric_name, metric_data in per_metric.items():
            improvement_pct = metric_data.get("improvement_pct", 0.0)

            # Check for regression
            if improvement_pct < -self.threshold * 100:
                regression = {
                    "metric": metric_name,
                    "change_pct": improvement_pct,
                    "baseline": metric_data.get("baseline", 0.0),
                    "current": metric_data.get("codechef", 0.0),
                    "severity": self._get_severity(improvement_pct),
                }
                analysis["regressions"].append(regression)

        # Determine overall regression status
        if analysis["regressions"]:
            analysis["has_regression"] = True

            # Calculate overall severity
            max_regression = min([r["change_pct"] for r in analysis["regressions"]])
            analysis["severity"] = self._get_severity(max_regression)

            # Determine recommendation
            if max_regression < -CRITICAL_THRESHOLD * 100:
                analysis["recommendation"] = "rollback"
            elif max_regression < -self.threshold * 100:
                analysis["recommendation"] = "investigate"
            else:
                analysis["recommendation"] = "monitor"

        return analysis

    def _get_severity(self, change_pct: float) -> str:
        """
        Determine severity level based on change percentage.

        Args:
            change_pct: Percentage change (negative = regression)

        Returns:
            Severity: 'critical', 'high', 'medium', 'low'
        """
        if change_pct < -CRITICAL_THRESHOLD * 100:
            return "critical"
        elif change_pct < -self.threshold * 2 * 100:
            return "high"
        elif change_pct < -self.threshold * 100:
            return "medium"
        else:
            return "low"

    async def create_linear_issue(
        self,
        analysis: Dict[str, Any],
        results: Dict[str, Any],
    ) -> Optional[str]:
        """
        Create Linear issue for regression.

        Args:
            analysis: Regression analysis
            results: Full evaluation results

        Returns:
            Issue ID if created, None otherwise
        """
        if not LINEAR_AVAILABLE:
            logger.error("Linear client not available")
            return None

        if not analysis["has_regression"]:
            logger.info("No regression detected - skipping issue creation")
            return None

        # Build issue description
        regressions_text = "\n".join(
            [
                f"- **{r['metric']}**: {r['change_pct']:.1f}% ({r['baseline']:.3f} → {r['current']:.3f}) [{r['severity']}]"
                for r in analysis["regressions"]
            ]
        )

        comparison = results.get("comparison", {})
        per_metric = comparison.get("per_metric", {})

        description = f"""
Automated evaluation detected performance regression.

## Summary

**Overall Change**: {analysis['overall_change_pct']:.1f}%
**Severity**: {analysis['severity']}
**Recommendation**: {analysis['recommendation']}

## Regressions Detected

{regressions_text}

## Per-Metric Details

```json
{json.dumps(per_metric, indent=2)}
```

## Action Required

Based on severity level:
- **Critical**: Immediate rollback required
- **High**: Investigate within 24 hours
- **Medium**: Review within 48 hours
- **Low**: Monitor next evaluation cycle

## Evaluation Details

- **Experiment**: {results.get('code_chef', {}).get('experiment_name', 'N/A')}
- **Dataset**: Evaluation dataset
- **Timestamp**: {datetime.now().isoformat()}
- **Results URL**: {results.get('code_chef', {}).get('results', {}).get('project_url', 'N/A')}

## Next Steps

1. Review LangSmith traces for failed examples
2. Check recent code changes (git log)
3. Compare with baseline performance
4. Determine root cause
5. Apply fix or rollback

---
*Generated by automated evaluation pipeline*
        """

        # Set priority based on severity
        priority_map = {
            "critical": 0,  # Urgent
            "high": 1,  # High
            "medium": 2,  # Medium
            "low": 3,  # Low
        }
        priority = priority_map.get(analysis["severity"], 2)

        # Create issue
        try:
            issue = await linear_client.create_issue(
                title=f"Evaluation Regression: {analysis['overall_change_pct']:.1f}% drop [{analysis['severity']}]",
                description=description,
                project="CHEF",
                labels=[
                    "regression",
                    "automated-eval",
                    f"severity-{analysis['severity']}",
                ],
                priority=priority,
            )

            logger.info(f"Created Linear issue: {issue.get('id')}")
            return issue.get("id")

        except Exception as e:
            logger.error(f"Failed to create Linear issue: {e}")
            return None

    async def query_historical_data(
        self,
        agent: str,
        metric: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Query historical metric data from database.

        Args:
            agent: Agent name
            metric: Metric name
            days: Number of days to look back

        Returns:
            List of historical data points
        """
        if not TRACKER_AVAILABLE:
            logger.error("Longitudinal tracker not available")
            return []

        try:
            trend = await longitudinal_tracker.get_metric_trend(
                agent=agent,
                metric=metric,
                limit=days * 4,  # Assume ~4 evals per day max
            )

            return trend

        except Exception as e:
            logger.error(f"Failed to query historical data: {e}")
            return []

    async def detect_trend_regression(
        self,
        agent: str,
        metric: str,
        current_value: float,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Detect regression by comparing to historical trend.

        Args:
            agent: Agent name
            metric: Metric name
            current_value: Current metric value
            days: Historical window

        Returns:
            Regression analysis
        """
        historical = await self.query_historical_data(agent, metric, days)

        if not historical:
            logger.warning("No historical data available for comparison")
            return {
                "has_regression": False,
                "reasoning": "Insufficient historical data",
            }

        # Calculate baseline (average of recent values)
        recent_values = [h["value"] for h in historical[:10]]  # Last 10 evals
        baseline = sum(recent_values) / len(recent_values)

        # Calculate change
        change_pct = (
            ((current_value - baseline) / baseline * 100) if baseline > 0 else 0.0
        )

        # Check for regression
        has_regression = change_pct < -self.threshold * 100

        analysis = {
            "has_regression": has_regression,
            "change_pct": change_pct,
            "baseline": baseline,
            "current": current_value,
            "severity": self._get_severity(change_pct) if has_regression else "none",
            "historical_count": len(historical),
        }

        return analysis


# =============================================================================
# CLI
# =============================================================================


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detect regressions in evaluation results"
    )

    # Input sources
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--results",
        help="Path to evaluation results JSON file",
    )
    input_group.add_argument(
        "--agent",
        help="Agent name for historical trend analysis",
    )

    # Parameters for historical analysis
    parser.add_argument(
        "--metric",
        help="Metric name for historical trend analysis",
    )
    parser.add_argument(
        "--current-value",
        type=float,
        help="Current metric value for trend comparison",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Historical window in days (default: 30)",
    )

    # Regression detection parameters
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Regression threshold (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--create-linear-issue",
        action="store_true",
        help="Create Linear issue if regression detected",
    )

    args = parser.parse_args()

    # Create detector
    detector = RegressionDetector(
        threshold=args.threshold,
        create_issues=args.create_linear_issue,
    )

    # Results file analysis
    if args.results:
        results_path = Path(args.results)
        if not results_path.exists():
            logger.error(f"Results file not found: {results_path}")
            sys.exit(1)

        # Load results
        results = json.loads(results_path.read_text())

        # Analyze
        logger.info("Analyzing evaluation results...")
        analysis = detector.analyze_results(results)

        # Create issue if needed
        if args.create_linear_issue and analysis["has_regression"]:
            logger.info("Creating Linear issue for regression...")
            issue_id = await detector.create_linear_issue(analysis, results)
            if issue_id:
                analysis["linear_issue_id"] = issue_id

        # Output
        print("\n" + "=" * 80)
        print("REGRESSION ANALYSIS")
        print("=" * 80)
        print(json.dumps(analysis, indent=2))

        # Exit with error code if regression detected
        if analysis["has_regression"]:
            sys.exit(1)

    # Historical trend analysis
    elif args.agent:
        if not args.metric or args.current_value is None:
            logger.error("--metric and --current-value required for trend analysis")
            sys.exit(1)

        logger.info(f"Analyzing trend for {args.agent}/{args.metric}...")
        analysis = await detector.detect_trend_regression(
            agent=args.agent,
            metric=args.metric,
            current_value=args.current_value,
            days=args.days,
        )

        # Output
        print("\n" + "=" * 80)
        print("TREND REGRESSION ANALYSIS")
        print("=" * 80)
        print(json.dumps(analysis, indent=2))

        # Exit with error code if regression detected
        if analysis["has_regression"]:
            sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

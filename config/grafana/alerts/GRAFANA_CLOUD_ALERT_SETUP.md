# Grafana Cloud Alert Configuration for Mode Hint Integration

This document describes how to configure alerts in Grafana Cloud for monitoring intent recognition performance with mode hints.

## Overview

These alerts monitor the effectiveness of mode hint integration and detect issues with intent classification accuracy.

## Access

- **Grafana Cloud URL**: https://appsmithery.grafana.net
- **Alerting Console**: https://appsmithery.grafana.net/alerting/list

## Alert Rules

### 1. Low Intent Confidence in Ask Mode

**Purpose**: Detect when intent recognition confidence drops in Ask mode, indicating potential classification issues.

**Configuration**:

1. Navigate to: https://appsmithery.grafana.net/alerting/list
2. Click "New alert rule"
3. Configure:
   - **Rule name**: `LowIntentConfidenceAskMode`
   - **Query A**:
     ```promql
     avg(orchestrator_intent_recognition_confidence{session_mode="ask"})
     ```
   - **Condition**: `WHEN avg() OF A IS BELOW 0.7`
   - **For**: `10m` (Alert after 10 minutes below threshold)
4. **Annotations**:
   - **Summary**: `Intent recognition confidence dropped in Ask mode`
   - **Description**: `Average confidence: {{ $values.A.Value }}`
5. **Labels**:

   - `severity`: `warning`
   - `component`: `intent_recognition`
   - `mode`: `ask`

6. **Notification policy**: Select your notification channel (email, Slack, etc.)

---

### 2. High False Positive Rate in Ask Mode

**Purpose**: Detect when too many Ask mode queries are incorrectly classified as task submissions.

**Configuration**:

1. Navigate to: https://appsmithery.grafana.net/alerting/list
2. Click "New alert rule"
3. Configure:
   - **Rule name**: `HighFalsePositiveRateAskMode`
   - **Query A** (Task submission rate in Ask mode):
     ```promql
     sum(rate(orchestrator_intent_recognition_total{intent_type="task_submission", session_mode="ask"}[1h]))
     ```
   - **Query B** (Total Ask mode requests):
     ```promql
     sum(rate(orchestrator_intent_recognition_total{session_mode="ask"}[1h]))
     ```
   - **Query C** (Percentage):
     ```promql
     $A / $B * 100
     ```
   - **Condition**: `WHEN last() OF C IS ABOVE 20`
   - **For**: `15m`
4. **Annotations**:
   - **Summary**: `20%+ of Ask mode queries classified as tasks (likely false positives)`
   - **Description**: `False positive rate: {{ $values.C.Value | humanizePercentage }}`
5. **Labels**:

   - `severity`: `warning`
   - `component`: `intent_recognition`
   - `mode`: `ask`
   - `issue_type`: `false_positive`

6. **Notification policy**: Select your notification channel

---

### 3. Mode Switch Spike

**Purpose**: Detect unusual patterns of users switching between Ask and Agent modes frequently.

**Configuration**:

1. Navigate to: https://appsmithery.grafana.net/alerting/list
2. Click "New alert rule"
3. Configure:
   - **Rule name**: `ModeSwitchSpike`
   - **Query A**:
     ```promql
     sum(rate(orchestrator_mode_switch_total[5m]))
     ```
   - **Condition**: `WHEN avg() OF A IS ABOVE 2` (More than 2 switches per second)
   - **For**: `5m`
4. **Annotations**:
   - **Summary**: `Unusually high mode switching detected`
   - **Description**: `Mode switches per second: {{ $values.A.Value | printf "%.2f" }}`
5. **Labels**:

   - `severity`: `info`
   - `component`: `intent_recognition`
   - `issue_type`: `ux_confusion`

6. **Notification policy**: Select your notification channel

---

### 4. Mode Hint Not Provided

**Purpose**: Track adoption of mode hints - alert if too many requests lack hints.

**Configuration**:

1. Navigate to: https://appsmithery.grafana.net/alerting/list
2. Click "New alert rule"
3. Configure:
   - **Rule name**: `ModeHintNotProvided`
   - **Query A** (Requests without hints):
     ```promql
     sum(rate(orchestrator_intent_recognition_total{mode_hint_source="none"}[1h]))
     ```
   - **Query B** (Total requests):
     ```promql
     sum(rate(orchestrator_intent_recognition_total[1h]))
     ```
   - **Query C** (Percentage):
     ```promql
     $A / $B * 100
     ```
   - **Condition**: `WHEN last() OF C IS ABOVE 30`
   - **For**: `30m`
4. **Annotations**:
   - **Summary**: `30%+ of requests missing mode hints`
   - **Description**: `Requests without hints: {{ $values.C.Value | humanizePercentage }}`
5. **Labels**:

   - `severity`: `info`
   - `component`: `intent_recognition`
   - `issue_type`: `adoption`

6. **Notification policy**: Select your notification channel

---

## Notification Channels

Configure notification channels at: https://appsmithery.grafana.net/alerting/notifications

Recommended channels:

1. **Email**: For critical alerts (severity: `critical`, `warning`)
2. **Slack**: For all alerts (real-time notifications)
3. **PagerDuty**: For production incidents (severity: `critical`)

## Testing Alerts

After configuration, test each alert:

1. Navigate to the alert rule
2. Click "Test alert rule"
3. Review the evaluation result
4. Verify notifications are sent correctly

## Maintenance

- **Review alert thresholds monthly** - Adjust based on actual usage patterns
- **Update alert descriptions** - Keep annotations current with system changes
- **Monitor alert fatigue** - Reduce noise by tuning thresholds

## Troubleshooting

### Alert not firing

1. Check metric availability:
   ```promql
   orchestrator_intent_recognition_total
   ```
2. Verify time range matches alert condition
3. Check notification channel configuration
4. Review alert history in Grafana Cloud

### False alerts

1. Review recent deployments (may cause temporary spikes)
2. Check if thresholds need adjustment
3. Verify metric calculations are correct

## Related Documentation

- [Tracing Schema](../../observability/tracing-schema.yaml) - Metadata definitions
- [Grafana Dashboard](../dashboards/intent-recognition-mode-analysis.json) - Visualization
- [Implementation Plan](../../../.github/prompts/plan-modeHintIntegration.prompt.md) - Technical details

## Support

For issues with alert configuration:

- **Grafana Cloud Support**: https://grafana.com/support
- **Internal**: Create Linear issue with label `observability`

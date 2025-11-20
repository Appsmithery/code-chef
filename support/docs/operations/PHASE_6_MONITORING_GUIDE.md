# Phase 6 Monitoring Guide

**Deployment Date**: November 19, 2025  
**Status**: ✅ Production Deployed  
**Droplet**: 45.55.173.72

## 📊 Monitoring Endpoints

### Prometheus Dashboards

- **Targets**: http://45.55.173.72:9090/targets
- **Metrics Browser**: http://45.55.173.72:9090/graph

### Agent Health Endpoints

```bash
# Orchestrator (EventBus + ResourceLock metrics)
curl http://45.55.173.72:8001/health
curl http://45.55.173.72:8001/metrics | grep event_bus

# Feature Development
curl http://45.55.173.72:8002/health

# Code Review
curl http://45.55.173.72:8003/health

# Infrastructure
curl http://45.55.173.72:8004/health

# CI/CD
curl http://45.55.173.72:8005/health

# Documentation
curl http://45.55.173.72:8006/health

# MCP Gateway
curl http://45.55.173.72:8000/health

# RAG Context
curl http://45.55.173.72:8007/health

# State Persistence
curl http://45.55.173.72:8008/health

# Agent Registry
curl http://45.55.173.72:8009/health
```

## 📈 Key Metrics to Monitor

### EventBus Metrics (Orchestrator)

```promql
# Event throughput (events/sec)
rate(event_bus_events_emitted_total[5m])

# Delivery success rate
rate(event_bus_events_delivered_total[5m]) / rate(event_bus_events_emitted_total[5m])

# Subscriber error rate
rate(event_bus_subscriber_errors_total[5m])

# Agent request latency (p95)
histogram_quantile(0.95, rate(agent_request_latency_seconds_bucket[5m]))

# Active requests (concurrent)
agent_requests_active

# Request timeout rate
rate(agent_request_timeouts_total[5m])
```

### ResourceLock Metrics (When Workflows Execute)

```promql
# Lock acquisition rate
rate(resource_lock_acquisitions_total[5m])

# Lock wait time (p95)
histogram_quantile(0.95, rate(resource_lock_wait_time_seconds_bucket[5m]))

# Active locks (concurrent)
resource_locks_active

# Lock contention rate
rate(resource_lock_contentions_total[5m])

# Lock timeout rate
rate(resource_lock_timeouts_total[5m])

# Lock contention ratio
rate(resource_lock_contentions_total[5m]) / rate(resource_lock_acquisitions_total[5m])
```

### Alert Thresholds (Recommended)

#### Critical Alerts

- **Event Bus Down**: `up{job="orchestrator"} == 0` for 5 minutes
- **High Error Rate**: `rate(event_bus_subscriber_errors_total[5m]) > 0.1`
- **Request Timeout Spike**: `rate(agent_request_timeouts_total[5m]) > 0.05`
- **Lock Timeout Spike**: `rate(resource_lock_timeouts_total[5m]) > 0.1`

#### Warning Alerts

- **High Latency**: `histogram_quantile(0.95, rate(agent_request_latency_seconds_bucket[5m])) > 2.0`
- **High Contention**: `rate(resource_lock_contentions_total[5m]) / rate(resource_lock_acquisitions_total[5m]) > 0.3`
- **Long Wait Times**: `histogram_quantile(0.95, rate(resource_lock_wait_time_seconds_bucket[5m])) > 5.0`

## 🔍 LangSmith Tracing

**Dashboard**: https://smith.langchain.com  
**Project**: `dev-tools-agents`

### Key Traces to Monitor

- **Session IDs**: Each workflow task has unique session_id
- **User IDs**: Agent names (orchestrator, feature-dev, etc.)
- **Costs**: Token usage per request
- **Latency**: LLM response times

### Useful Filters

```
tags:orchestrator
tags:multi-agent
session_id:<task_id>
user_id:orchestrator
```

## 📋 48-Hour Monitoring Checklist

### Day 1 (First 24 Hours)

- [ ] Verify all 10+ Prometheus targets are UP (check every 4 hours)
- [ ] Monitor EventBus throughput baseline
- [ ] Watch for subscriber errors
- [ ] Check agent request latency patterns
- [ ] Verify agent-registry is healthy
- [ ] Review LangSmith traces for orchestrator workflows

### Day 2 (24-48 Hours)

- [ ] Compare metrics against Day 1 baseline
- [ ] Check for memory leaks (container stats)
- [ ] Verify PostgreSQL connection pool health
- [ ] Review any timeout patterns
- [ ] Validate lock contention stays < 30%
- [ ] Check disk usage on droplet

### Post-48 Hours

- [ ] Document baseline metrics
- [ ] Set up Prometheus alerts
- [ ] Configure Slack/email notifications
- [ ] Mark PR-68 complete in Linear
- [ ] Archive monitoring logs

## 🚨 Troubleshooting

### High Event Bus Errors

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools/deploy
docker compose logs orchestrator -n 200 | grep ERROR
```

### ResourceLock Deadlocks

```bash
# Check PostgreSQL advisory locks
docker compose exec postgres psql -U devtools -d devtools -c "
SELECT
    locktype,
    database,
    classid,
    objid,
    pid,
    mode,
    granted
FROM pg_locks
WHERE locktype = 'advisory';"
```

### Agent Unresponsive

```bash
# Restart specific agent
docker compose restart orchestrator

# Check health
curl http://localhost:8001/health
```

### Memory Issues

```bash
# Check container memory usage
docker stats --no-stream

# Restart services if needed
docker compose restart
```

## 📞 Escalation Contacts

- **On-Call**: alex@appsmithery.co
- **Linear Workspace**: PR-68 (approval hub)
- **LangSmith Project**: dev-tools-agents
- **Droplet**: 45.55.173.72 (DigitalOcean)

## 🔗 Related Documentation

- `PHASE_6_COMPLETE.md` - Implementation details
- `EVENT_PROTOCOL.md` - Event bus usage patterns
- `RESOURCE_LOCKING.md` - Locking best practices
- `AGENT_REGISTRY.md` - Agent discovery system
- `support/scripts/validate-phase6.ps1` - Validation script

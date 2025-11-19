-- Workflow State Management Schema
-- Supports LangGraph checkpointing for multi-agent workflows
-- Part of Phase 6: Multi-Agent Collaboration

-- ============================================================================
-- WORKFLOW STATE TABLE
-- ============================================================================
-- Stores metadata and current state for multi-agent workflows
CREATE TABLE IF NOT EXISTS workflow_state (
    workflow_id VARCHAR(64) PRIMARY KEY,
    workflow_type VARCHAR(64) NOT NULL,
    current_step VARCHAR(128) NOT NULL,
    state_data JSONB NOT NULL,
    participating_agents TEXT[],
    started_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(32) NOT NULL CHECK (status IN ('running', 'paused', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_workflow_status ON workflow_state(status);
CREATE INDEX IF NOT EXISTS idx_workflow_updated ON workflow_state(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_type ON workflow_state(workflow_type);
CREATE INDEX IF NOT EXISTS idx_workflow_started ON workflow_state(started_at DESC);

-- ============================================================================
-- WORKFLOW CHECKPOINTS TABLE
-- ============================================================================
-- Stores step-by-step checkpoints for state recovery
CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    checkpoint_id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(64) NOT NULL REFERENCES workflow_state(workflow_id) ON DELETE CASCADE,
    step_name VARCHAR(128) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    checkpoint_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    duration_ms INTEGER,
    status VARCHAR(32) NOT NULL CHECK (status IN ('success', 'error', 'timeout', 'skipped'))
);

-- Indexes for checkpoint queries
CREATE INDEX IF NOT EXISTS idx_checkpoint_workflow ON workflow_checkpoints(workflow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_checkpoint_agent ON workflow_checkpoints(agent_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_step ON workflow_checkpoints(step_name);

-- ============================================================================
-- LANGGRAPH CHECKPOINTER TABLE
-- ============================================================================
-- Native LangGraph checkpoint storage (PostgresSaver format)
-- Schema matches langgraph.checkpoint.postgres.PostgresSaver requirements
CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_langgraph_thread ON langgraph_checkpoints(thread_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_langgraph_parent ON langgraph_checkpoints(parent_checkpoint_id);

-- ============================================================================
-- LANGGRAPH WRITES TABLE
-- ============================================================================
-- Stores pending writes for LangGraph checkpointing
CREATE TABLE IF NOT EXISTS langgraph_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE INDEX IF NOT EXISTS idx_langgraph_writes_thread ON langgraph_writes(thread_id, checkpoint_id);

-- ============================================================================
-- AUTO-CLEANUP FUNCTIONS
-- ============================================================================

-- Function: Update workflow updated_at timestamp
CREATE OR REPLACE FUNCTION update_workflow_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update timestamp on workflow changes
DROP TRIGGER IF EXISTS trigger_update_workflow_timestamp ON workflow_state;
CREATE TRIGGER trigger_update_workflow_timestamp
    BEFORE UPDATE ON workflow_state
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_timestamp();

-- Function: Cleanup old completed workflows
CREATE OR REPLACE FUNCTION cleanup_old_workflows()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete workflows completed more than 30 days ago
    DELETE FROM workflow_state
    WHERE status = 'completed'
    AND completed_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Cleanup orphaned checkpoints
CREATE OR REPLACE FUNCTION cleanup_orphaned_checkpoints()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete checkpoints with no corresponding workflow
    DELETE FROM workflow_checkpoints
    WHERE workflow_id NOT IN (SELECT workflow_id FROM workflow_state);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Cleanup old LangGraph checkpoints
CREATE OR REPLACE FUNCTION cleanup_old_langgraph_checkpoints()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Keep only last 100 checkpoints per thread, delete older ones
    WITH ranked_checkpoints AS (
        SELECT 
            thread_id,
            checkpoint_ns,
            checkpoint_id,
            ROW_NUMBER() OVER (PARTITION BY thread_id, checkpoint_ns ORDER BY created_at DESC) as rn
        FROM langgraph_checkpoints
    )
    DELETE FROM langgraph_checkpoints
    WHERE (thread_id, checkpoint_ns, checkpoint_id) IN (
        SELECT thread_id, checkpoint_ns, checkpoint_id
        FROM ranked_checkpoints
        WHERE rn > 100
    );
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS FOR MONITORING
-- ============================================================================

-- Active workflows view
CREATE OR REPLACE VIEW active_workflows AS
SELECT 
    workflow_id,
    workflow_type,
    current_step,
    status,
    participating_agents,
    started_at,
    updated_at,
    EXTRACT(EPOCH FROM (NOW() - started_at)) as duration_seconds,
    (SELECT COUNT(*) FROM workflow_checkpoints WHERE workflow_id = ws.workflow_id) as checkpoint_count
FROM workflow_state ws
WHERE status IN ('running', 'paused')
ORDER BY started_at DESC;

-- Workflow statistics view
CREATE OR REPLACE VIEW workflow_statistics AS
SELECT 
    workflow_type,
    COUNT(*) as total_workflows,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
    COUNT(*) FILTER (WHERE status = 'running') as running_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE status = 'completed') as avg_duration_seconds,
    MAX(updated_at) as last_execution
FROM workflow_state
GROUP BY workflow_type
ORDER BY total_workflows DESC;

-- Recent checkpoint activity view
CREATE OR REPLACE VIEW recent_checkpoints AS
SELECT 
    wc.workflow_id,
    ws.workflow_type,
    wc.step_name,
    wc.agent_id,
    wc.status,
    wc.duration_ms,
    wc.created_at
FROM workflow_checkpoints wc
JOIN workflow_state ws ON wc.workflow_id = ws.workflow_id
ORDER BY wc.created_at DESC
LIMIT 100;

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Uncomment to insert sample workflow for testing
/*
INSERT INTO workflow_state (
    workflow_id,
    workflow_type,
    current_step,
    state_data,
    participating_agents,
    started_at,
    updated_at,
    status
) VALUES (
    'test-workflow-001',
    'pr_deployment',
    'code_review',
    '{"pr_number": 123, "repo_url": "https://github.com/test/repo"}'::jsonb,
    ARRAY['orchestrator', 'code-review', 'cicd'],
    NOW(),
    NOW(),
    'running'
);
*/

-- ============================================================================
-- GRANTS (adjust as needed for your security model)
-- ============================================================================

-- Grant permissions to devtools user (adjust username as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON workflow_state TO devtools;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON workflow_checkpoints TO devtools;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON langgraph_checkpoints TO devtools;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON langgraph_writes TO devtools;
-- GRANT USAGE, SELECT ON SEQUENCE workflow_checkpoints_checkpoint_id_seq TO devtools;
-- GRANT SELECT ON active_workflows TO devtools;
-- GRANT SELECT ON workflow_statistics TO devtools;
-- GRANT SELECT ON recent_checkpoints TO devtools;

-- ============================================================================
-- MAINTENANCE QUERIES
-- ============================================================================

-- Run cleanup functions (add to cron or scheduled task)
-- SELECT cleanup_old_workflows();
-- SELECT cleanup_orphaned_checkpoints();
-- SELECT cleanup_old_langgraph_checkpoints();

-- Check workflow health
-- SELECT * FROM workflow_statistics;
-- SELECT * FROM active_workflows;
-- SELECT * FROM recent_checkpoints;

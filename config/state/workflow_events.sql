-- Event Sourcing Schema for Workflow Management
-- Implements immutable event log with snapshots for performance
-- Week 4: Stateless Reducers & Event Replay (DEV-174)

-- ============================================================================
-- WORKFLOW EVENTS TABLE
-- ============================================================================
-- Immutable event log - single source of truth for workflow state
-- Events are NEVER updated or deleted (only archived after retention period)

CREATE TABLE IF NOT EXISTS workflow_events (
    -- Event identification
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL,
    parent_workflow_id VARCHAR(255),  -- Task 5.1: Parent workflow for child workflows
    
    -- Event metadata
    action VARCHAR(50) NOT NULL,
    step_id VARCHAR(255),
    event_version INTEGER DEFAULT 2,
    
    -- Event data (flexible JSON)
    data JSONB DEFAULT '{}',
    
    -- Audit trail
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signature VARCHAR(64),  -- HMAC-SHA256 for tamper detection
    
    -- Indexing
    CONSTRAINT valid_action CHECK (action IN (
        'start_workflow',
        'complete_step',
        'fail_step',
        'approve_gate',
        'reject_gate',
        'pause_workflow',
        'resume_workflow',
        'rollback_step',
        'cancel_workflow',
        'retry_step',
        'start_child_workflow',
        'child_workflow_complete',
        'create_snapshot',
        'annotate'
    ))
);

-- Indexes for fast event retrieval
CREATE INDEX IF NOT EXISTS idx_workflow_events_workflow_id 
    ON workflow_events(workflow_id);

CREATE INDEX IF NOT EXISTS idx_workflow_events_workflow_timestamp 
    ON workflow_events(workflow_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_workflow_events_action 
    ON workflow_events(action);

-- Index for time-travel queries
CREATE INDEX IF NOT EXISTS idx_workflow_events_timestamp 
    ON workflow_events(timestamp);

-- GIN index for JSONB queries (find events by data content)
CREATE INDEX IF NOT EXISTS idx_workflow_events_data 
    ON workflow_events USING GIN(data);

-- Task 5.1: Index for parent workflow chain traversal
CREATE INDEX IF NOT EXISTS idx_workflow_events_parent 
    ON workflow_events(parent_workflow_id) WHERE parent_workflow_id IS NOT NULL;


-- ============================================================================
-- WORKFLOW SNAPSHOTS TABLE
-- ============================================================================
-- Periodic state snapshots for performance optimization
-- Enables fast state reconstruction: snapshot + delta events

CREATE TABLE IF NOT EXISTS workflow_snapshots (
    -- Snapshot identification
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL,
    
    -- Snapshot data (full state at this point)
    state JSONB NOT NULL,
    
    -- Snapshot metadata
    event_count INTEGER NOT NULL,  -- Number of events up to this snapshot
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Compression flag (for future optimization)
    compressed BOOLEAN DEFAULT FALSE
);

-- Indexes for fast snapshot retrieval
CREATE INDEX IF NOT EXISTS idx_workflow_snapshots_workflow_id 
    ON workflow_snapshots(workflow_id);

-- Get most recent snapshot first
CREATE INDEX IF NOT EXISTS idx_workflow_snapshots_workflow_created 
    ON workflow_snapshots(workflow_id, created_at DESC);


-- ============================================================================
-- WORKFLOW METADATA TABLE (Optional)
-- ============================================================================
-- Summary information for fast workflow listing
-- Derived from events but cached for performance

CREATE TABLE IF NOT EXISTS workflow_metadata (
    workflow_id VARCHAR(255) PRIMARY KEY,
    
    -- Workflow info
    template_name VARCHAR(255),
    template_version VARCHAR(50),
    
    -- Status (derived from latest events)
    status VARCHAR(50) NOT NULL,
    current_step VARCHAR(255),
    
    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    
    -- Summary counts
    total_events INTEGER DEFAULT 0,
    steps_completed INTEGER DEFAULT 0,
    steps_failed INTEGER DEFAULT 0,
    
    -- Latest snapshot reference
    latest_snapshot_id UUID REFERENCES workflow_snapshots(snapshot_id),
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_metadata_status 
    ON workflow_metadata(status);

CREATE INDEX IF NOT EXISTS idx_workflow_metadata_template 
    ON workflow_metadata(template_name);


-- ============================================================================
-- EVENT ARCHIVE TABLE
-- ============================================================================
-- Archive for events older than retention period (90 days)
-- Structure identical to workflow_events but for cold storage

CREATE TABLE IF NOT EXISTS workflow_events_archive (
    LIKE workflow_events INCLUDING ALL
);

-- Partition by year-month for efficient archival
CREATE INDEX IF NOT EXISTS idx_workflow_events_archive_timestamp 
    ON workflow_events_archive(timestamp);


-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update workflow metadata when events inserted
CREATE OR REPLACE FUNCTION update_workflow_metadata()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO workflow_metadata (workflow_id, status, total_events, updated_at)
    VALUES (NEW.workflow_id, 'running', 1, NOW())
    ON CONFLICT (workflow_id) DO UPDATE SET
        total_events = workflow_metadata.total_events + 1,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update metadata
CREATE TRIGGER trigger_update_workflow_metadata
AFTER INSERT ON workflow_events
FOR EACH ROW
EXECUTE FUNCTION update_workflow_metadata();


-- Function to archive old events (run via cron job)
CREATE OR REPLACE FUNCTION archive_old_events(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Move events older than retention period to archive
    WITH archived AS (
        DELETE FROM workflow_events
        WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL
        RETURNING *
    )
    INSERT INTO workflow_events_archive
    SELECT * FROM archived;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;


-- Function to verify event signature integrity
CREATE OR REPLACE FUNCTION verify_event_signatures(p_workflow_id VARCHAR)
RETURNS TABLE(event_id UUID, is_valid BOOLEAN, error_message TEXT) AS $$
BEGIN
    -- This is a placeholder for signature verification
    -- Actual verification happens in application code
    RETURN QUERY
    SELECT 
        e.event_id,
        (e.signature IS NOT NULL) AS is_valid,
        CASE 
            WHEN e.signature IS NULL THEN 'No signature (V1 event)'
            ELSE NULL
        END AS error_message
    FROM workflow_events e
    WHERE e.workflow_id = p_workflow_id
    ORDER BY e.timestamp;
END;
$$ LANGUAGE plpgsql;


-- Function to get workflow state from events (replay in SQL)
-- Note: This is expensive, prefer application-level replay
CREATE OR REPLACE FUNCTION get_workflow_event_count(p_workflow_id VARCHAR)
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM workflow_events WHERE workflow_id = p_workflow_id);
END;
$$ LANGUAGE plpgsql;


-- Function to create snapshot from current events
CREATE OR REPLACE FUNCTION create_workflow_snapshot(
    p_workflow_id VARCHAR,
    p_state JSONB
)
RETURNS UUID AS $$
DECLARE
    v_snapshot_id UUID;
    v_event_count INTEGER;
BEGIN
    -- Get current event count
    SELECT COUNT(*) INTO v_event_count
    FROM workflow_events
    WHERE workflow_id = p_workflow_id;
    
    -- Create snapshot
    INSERT INTO workflow_snapshots (workflow_id, state, event_count)
    VALUES (p_workflow_id, p_state, v_event_count)
    RETURNING snapshot_id INTO v_snapshot_id;
    
    -- Update metadata with latest snapshot
    UPDATE workflow_metadata
    SET latest_snapshot_id = v_snapshot_id,
        updated_at = NOW()
    WHERE workflow_id = p_workflow_id;
    
    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql;


-- Function to cleanup old snapshots (keep only last 3)
CREATE OR REPLACE FUNCTION cleanup_old_snapshots(p_workflow_id VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH old_snapshots AS (
        SELECT snapshot_id
        FROM workflow_snapshots
        WHERE workflow_id = p_workflow_id
        ORDER BY created_at DESC
        OFFSET 3  -- Keep last 3 snapshots
    )
    DELETE FROM workflow_snapshots
    WHERE snapshot_id IN (SELECT snapshot_id FROM old_snapshots);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for active workflows (not completed/failed/cancelled)
CREATE OR REPLACE VIEW active_workflows AS
SELECT 
    m.workflow_id,
    m.template_name,
    m.status,
    m.current_step,
    m.started_at,
    m.total_events,
    m.steps_completed,
    NOW() - m.started_at AS duration
FROM workflow_metadata m
WHERE m.status IN ('running', 'paused')
ORDER BY m.started_at DESC;


-- View for workflow event timeline (with human-readable timestamps)
CREATE OR REPLACE VIEW workflow_event_timeline AS
SELECT 
    e.workflow_id,
    e.event_id,
    e.action,
    e.step_id,
    e.timestamp,
    e.data,
    ROW_NUMBER() OVER (PARTITION BY e.workflow_id ORDER BY e.timestamp) AS event_number,
    LAG(e.timestamp) OVER (PARTITION BY e.workflow_id ORDER BY e.timestamp) AS previous_event_timestamp,
    e.timestamp - LAG(e.timestamp) OVER (PARTITION BY e.workflow_id ORDER BY e.timestamp) AS time_since_previous
FROM workflow_events e
ORDER BY e.workflow_id, e.timestamp;


-- View for workflow approval history
CREATE OR REPLACE VIEW workflow_approvals AS
SELECT 
    e.workflow_id,
    e.step_id,
    e.action,
    e.data->>'approver' AS approver,
    e.data->>'approver_role' AS approver_role,
    e.data->>'comment' AS comment,
    e.timestamp AS approval_timestamp
FROM workflow_events e
WHERE e.action IN ('approve_gate', 'reject_gate')
ORDER BY e.workflow_id, e.timestamp;


-- ============================================================================
-- GRANTS (adjust for your user)
-- ============================================================================

-- Grant read/write access to workflow service
-- GRANT SELECT, INSERT ON workflow_events TO workflow_service;
-- GRANT SELECT, INSERT, UPDATE ON workflow_snapshots TO workflow_service;
-- GRANT SELECT, UPDATE ON workflow_metadata TO workflow_service;

-- Grant read-only access to analytics/reporting
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_readonly;
-- GRANT SELECT ON active_workflows, workflow_event_timeline, workflow_approvals TO analytics_readonly;


-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE workflow_events IS 
'Immutable event log for workflow state transitions. Single source of truth.';

COMMENT ON COLUMN workflow_events.signature IS 
'HMAC-SHA256 signature for tamper detection. Computed over all fields except signature itself.';

COMMENT ON TABLE workflow_snapshots IS 
'Periodic state snapshots for performance. Enables fast reconstruction: snapshot + delta events.';

COMMENT ON TABLE workflow_metadata IS 
'Cached workflow summary for fast listing. Derived from events via triggers.';

COMMENT ON FUNCTION archive_old_events IS 
'Archive events older than retention period (default: 90 days). Run via cron job.';

COMMENT ON FUNCTION create_workflow_snapshot IS 
'Create state snapshot for workflow. Call every 10 events for optimal performance.';

COMMENT ON VIEW active_workflows IS 
'Workflows currently running or paused (not completed/failed/cancelled).';


-- ============================================================================
-- TASK 5.3: WORKFLOW TTL MANAGEMENT (Week 5 Zen Pattern Integration)
-- ============================================================================

-- Workflow TTL tracking table
CREATE TABLE IF NOT EXISTS workflow_ttl (
    workflow_id VARCHAR(255) PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refresh_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for cleanup queries (find expired workflows)
CREATE INDEX IF NOT EXISTS idx_workflow_ttl_expires 
    ON workflow_ttl(expires_at);

-- Function to cleanup expired workflows (run via cron job)
CREATE OR REPLACE FUNCTION cleanup_expired_workflows()
RETURNS TABLE(workflow_id VARCHAR, expired_at TIMESTAMPTZ, event_count INTEGER) AS $$
BEGIN
    RETURN QUERY
    WITH expired AS (
        SELECT t.workflow_id, t.expires_at
        FROM workflow_ttl t
        WHERE t.expires_at < NOW()
    ),
    archived_events AS (
        DELETE FROM workflow_events e
        USING expired x
        WHERE e.workflow_id = x.workflow_id
        RETURNING e.workflow_id, COUNT(*) OVER (PARTITION BY e.workflow_id) AS cnt
    ),
    deleted_ttl AS (
        DELETE FROM workflow_ttl t
        USING expired x
        WHERE t.workflow_id = x.workflow_id
        RETURNING t.workflow_id, t.expires_at
    )
    SELECT DISTINCT 
        d.workflow_id, 
        d.expires_at AS expired_at,
        COALESCE(a.cnt, 0) AS event_count
    FROM deleted_ttl d
    LEFT JOIN archived_events a ON d.workflow_id = a.workflow_id;
END;
$$ LANGUAGE plpgsql;


-- View for active workflows with TTL status
CREATE OR REPLACE VIEW active_workflows_with_ttl AS
SELECT 
    m.workflow_id,
    m.template_name,
    m.status,
    m.started_at,
    m.total_events,
    t.expires_at,
    t.refreshed_at,
    t.refresh_count,
    t.expires_at - NOW() AS time_until_expiration,
    EXTRACT(EPOCH FROM (NOW() - t.refreshed_at)) AS seconds_since_refresh
FROM workflow_metadata m
LEFT JOIN workflow_ttl t ON m.workflow_id = t.workflow_id
WHERE m.status IN ('running', 'paused')
ORDER BY t.expires_at NULLS LAST;


COMMENT ON TABLE workflow_ttl IS 
'TTL tracking for workflow auto-expiration (Task 5.3 - Week 5 Zen Pattern Integration). Active workflows refresh TTL on every event, abandoned workflows auto-expire.';

COMMENT ON FUNCTION cleanup_expired_workflows IS 
'Cleanup expired workflows by deleting events and TTL records. Returns list of cleaned up workflows.';

COMMENT ON VIEW active_workflows_with_ttl IS 
'Active workflows with TTL status (time until expiration, refresh count).';


-- ============================================================================
-- TASK 5.1: PARENT WORKFLOW CHAINS (Week 5 Zen Pattern Integration)
-- ============================================================================

-- Migration function to add parent_workflow_id column (idempotent)
CREATE OR REPLACE FUNCTION migrate_parent_workflow_id()
RETURNS TEXT AS $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    -- Check if column already exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'workflow_events' 
        AND column_name = 'parent_workflow_id'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        -- Add column
        ALTER TABLE workflow_events 
        ADD COLUMN parent_workflow_id VARCHAR(255);
        
        -- Add index
        CREATE INDEX idx_workflow_events_parent 
        ON workflow_events(parent_workflow_id) 
        WHERE parent_workflow_id IS NOT NULL;
        
        RETURN 'Migration complete: Added parent_workflow_id column and index';
    ELSE
        RETURN 'Migration skipped: parent_workflow_id column already exists';
    END IF;
END;
$$ LANGUAGE plpgsql;


-- Validation function to check for orphaned parent references
CREATE OR REPLACE FUNCTION validate_parent_workflow_references()
RETURNS TABLE(orphaned_workflow_id VARCHAR, parent_workflow_id VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT we1.workflow_id, we1.parent_workflow_id
    FROM workflow_events we1
    WHERE we1.parent_workflow_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM workflow_events we2
        WHERE we2.workflow_id = we1.parent_workflow_id
    );
END;
$$ LANGUAGE plpgsql;


-- View for workflow chains (parent-child relationships)
CREATE OR REPLACE VIEW workflow_chains AS
WITH RECURSIVE workflow_hierarchy AS (
    -- Root workflows (no parent)
    SELECT 
        workflow_id,
        template_name,
        status,
        started_at,
        parent_workflow_id,
        workflow_id AS root_workflow_id,
        1 AS depth,
        ARRAY[workflow_id] AS chain_path
    FROM workflow_metadata
    WHERE parent_workflow_id IS NULL
    
    UNION ALL
    
    -- Child workflows
    SELECT 
        m.workflow_id,
        m.template_name,
        m.status,
        m.started_at,
        m.parent_workflow_id,
        h.root_workflow_id,
        h.depth + 1,
        h.chain_path || m.workflow_id
    FROM workflow_metadata m
    INNER JOIN workflow_hierarchy h ON m.parent_workflow_id = h.workflow_id
    WHERE h.depth < 20  -- Prevent infinite loops
)
SELECT 
    workflow_id,
    template_name,
    status,
    parent_workflow_id,
    root_workflow_id,
    depth,
    chain_path,
    ARRAY_LENGTH(chain_path, 1) AS chain_length
FROM workflow_hierarchy
ORDER BY root_workflow_id, depth;


COMMENT ON COLUMN workflow_events.parent_workflow_id IS 
'Parent workflow ID for child workflows (Task 5.1 - Week 5 Zen Pattern Integration). Enables complete audit trails across workflow composition.';

COMMENT ON FUNCTION validate_parent_workflow_references IS 
'Check for orphaned parent references (workflows referencing non-existent parents).';

COMMENT ON VIEW workflow_chains IS 
'Hierarchical view of parent-child workflow relationships with depth and chain path.';

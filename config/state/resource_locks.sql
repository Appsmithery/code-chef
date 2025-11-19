-- Resource Locking Schema for Multi-Agent Coordination
-- Implements PostgreSQL advisory locks with metadata tracking
-- Part of Phase 6: Multi-Agent Collaboration - Task 6.4

-- ============================================================================
-- RESOURCE LOCKS TABLE
-- ============================================================================
-- Tracks lock ownership and metadata for debugging and monitoring
CREATE TABLE IF NOT EXISTS resource_locks (
    resource_id VARCHAR(256) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    acquired_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    lock_key BIGINT NOT NULL,  -- PostgreSQL advisory lock key
    reason VARCHAR(512),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_expiry CHECK (expires_at > acquired_at)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_lock_expiry ON resource_locks(expires_at);
CREATE INDEX IF NOT EXISTS idx_lock_agent ON resource_locks(agent_id);
CREATE INDEX IF NOT EXISTS idx_lock_acquired ON resource_locks(acquired_at DESC);

-- ============================================================================
-- LOCK HISTORY TABLE
-- ============================================================================
-- Audit trail of all lock operations
CREATE TABLE IF NOT EXISTS lock_history (
    history_id SERIAL PRIMARY KEY,
    resource_id VARCHAR(256) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    operation VARCHAR(32) NOT NULL CHECK (operation IN ('acquire', 'release', 'timeout', 'force_release')),
    acquired_at TIMESTAMP,
    released_at TIMESTAMP,
    duration_ms INTEGER,
    wait_time_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_history_resource ON lock_history(resource_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_agent ON lock_history(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_operation ON lock_history(operation);

-- ============================================================================
-- LOCK WAIT QUEUE TABLE
-- ============================================================================
-- Track agents waiting for locks
CREATE TABLE IF NOT EXISTS lock_wait_queue (
    queue_id SERIAL PRIMARY KEY,
    resource_id VARCHAR(256) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    timeout_at TIMESTAMP NOT NULL,
    priority INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_queue_resource ON lock_wait_queue(resource_id, requested_at);
CREATE INDEX IF NOT EXISTS idx_queue_timeout ON lock_wait_queue(timeout_at);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Convert resource_id string to bigint for advisory lock
CREATE OR REPLACE FUNCTION resource_id_to_lock_key(resource_id_text VARCHAR)
RETURNS BIGINT AS $$
BEGIN
    -- Use hashtext to convert string to consistent integer
    RETURN hashtext(resource_id_text)::BIGINT;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- ACQUIRE LOCK FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION acquire_resource_lock(
    p_resource_id VARCHAR,
    p_agent_id VARCHAR,
    p_timeout_seconds INTEGER DEFAULT 300,
    p_reason VARCHAR DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE(
    success BOOLEAN,
    lock_acquired BOOLEAN,
    message TEXT,
    wait_time_ms INTEGER
) AS $$
DECLARE
    v_lock_key BIGINT;
    v_lock_acquired BOOLEAN;
    v_start_time TIMESTAMP;
    v_wait_time_ms INTEGER;
    v_existing_owner VARCHAR;
    v_existing_expiry TIMESTAMP;
BEGIN
    v_start_time := clock_timestamp();
    v_lock_key := resource_id_to_lock_key(p_resource_id);
    
    -- Check if lock already exists
    SELECT agent_id, expires_at INTO v_existing_owner, v_existing_expiry
    FROM resource_locks
    WHERE resource_id = p_resource_id;
    
    -- Clean up expired lock if found
    IF v_existing_expiry IS NOT NULL AND v_existing_expiry < NOW() THEN
        PERFORM release_resource_lock(p_resource_id, v_existing_owner);
        v_existing_owner := NULL;
    END IF;
    
    -- Try to acquire PostgreSQL advisory lock (non-blocking)
    v_lock_acquired := pg_try_advisory_lock(v_lock_key);
    
    IF v_lock_acquired THEN
        -- Success - insert metadata
        INSERT INTO resource_locks (
            resource_id, agent_id, acquired_at, expires_at,
            lock_key, reason, metadata
        ) VALUES (
            p_resource_id,
            p_agent_id,
            NOW(),
            NOW() + (p_timeout_seconds || ' seconds')::INTERVAL,
            v_lock_key,
            p_reason,
            p_metadata
        )
        ON CONFLICT (resource_id) DO UPDATE SET
            agent_id = p_agent_id,
            acquired_at = NOW(),
            expires_at = NOW() + (p_timeout_seconds || ' seconds')::INTERVAL,
            reason = p_reason,
            metadata = p_metadata;
        
        v_wait_time_ms := EXTRACT(MILLISECONDS FROM (clock_timestamp() - v_start_time))::INTEGER;
        
        -- Log success
        INSERT INTO lock_history (
            resource_id, agent_id, operation, acquired_at,
            duration_ms, wait_time_ms, success
        ) VALUES (
            p_resource_id, p_agent_id, 'acquire', NOW(),
            NULL, v_wait_time_ms, TRUE
        );
        
        RETURN QUERY SELECT TRUE, TRUE, 'Lock acquired successfully'::TEXT, v_wait_time_ms;
    ELSE
        -- Lock held by another agent
        v_wait_time_ms := EXTRACT(MILLISECONDS FROM (clock_timestamp() - v_start_time))::INTEGER;
        
        -- Add to wait queue
        INSERT INTO lock_wait_queue (
            resource_id, agent_id, requested_at, timeout_at, metadata
        ) VALUES (
            p_resource_id,
            p_agent_id,
            NOW(),
            NOW() + (p_timeout_seconds || ' seconds')::INTERVAL,
            p_metadata
        );
        
        -- Log failure
        INSERT INTO lock_history (
            resource_id, agent_id, operation, wait_time_ms, success, error_message
        ) VALUES (
            p_resource_id, p_agent_id, 'acquire', v_wait_time_ms, FALSE,
            'Lock held by: ' || COALESCE(v_existing_owner, 'unknown')
        );
        
        RETURN QUERY SELECT 
            TRUE,
            FALSE,
            ('Lock held by agent: ' || COALESCE(v_existing_owner, 'unknown') || 
             ', expires at: ' || COALESCE(v_existing_expiry::TEXT, 'unknown'))::TEXT,
            v_wait_time_ms;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- RELEASE LOCK FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION release_resource_lock(
    p_resource_id VARCHAR,
    p_agent_id VARCHAR
)
RETURNS TABLE(
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    v_lock_key BIGINT;
    v_acquired_at TIMESTAMP;
    v_duration_ms INTEGER;
    v_current_owner VARCHAR;
BEGIN
    v_lock_key := resource_id_to_lock_key(p_resource_id);
    
    -- Get current lock owner
    SELECT agent_id, acquired_at INTO v_current_owner, v_acquired_at
    FROM resource_locks
    WHERE resource_id = p_resource_id;
    
    -- Verify ownership (allow release if lock expired or no owner)
    IF v_current_owner IS NULL OR v_current_owner = p_agent_id OR 
       (SELECT expires_at FROM resource_locks WHERE resource_id = p_resource_id) < NOW() THEN
        
        -- Calculate duration
        IF v_acquired_at IS NOT NULL THEN
            v_duration_ms := EXTRACT(MILLISECONDS FROM (NOW() - v_acquired_at))::INTEGER;
        END IF;
        
        -- Release PostgreSQL advisory lock
        PERFORM pg_advisory_unlock(v_lock_key);
        
        -- Remove metadata
        DELETE FROM resource_locks WHERE resource_id = p_resource_id;
        
        -- Remove from wait queue
        DELETE FROM lock_wait_queue WHERE resource_id = p_resource_id AND agent_id = p_agent_id;
        
        -- Log release
        INSERT INTO lock_history (
            resource_id, agent_id, operation, acquired_at, released_at,
            duration_ms, success
        ) VALUES (
            p_resource_id, p_agent_id, 'release', v_acquired_at, NOW(),
            v_duration_ms, TRUE
        );
        
        RETURN QUERY SELECT TRUE, 'Lock released successfully'::TEXT;
    ELSE
        -- Not the owner
        RETURN QUERY SELECT 
            FALSE,
            ('Lock owned by different agent: ' || v_current_owner)::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CHECK LOCK STATUS FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION check_lock_status(p_resource_id VARCHAR)
RETURNS TABLE(
    is_locked BOOLEAN,
    owner_agent_id VARCHAR,
    acquired_at TIMESTAMP,
    expires_at TIMESTAMP,
    seconds_remaining INTEGER,
    reason VARCHAR,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        TRUE as is_locked,
        rl.agent_id,
        rl.acquired_at,
        rl.expires_at,
        GREATEST(0, EXTRACT(EPOCH FROM (rl.expires_at - NOW()))::INTEGER) as seconds_remaining,
        rl.reason,
        rl.metadata
    FROM resource_locks rl
    WHERE rl.resource_id = p_resource_id
    AND rl.expires_at > NOW();
    
    -- Return empty result if not found (is_locked will be NULL)
    IF NOT FOUND THEN
        RETURN QUERY SELECT 
            FALSE as is_locked,
            NULL::VARCHAR,
            NULL::TIMESTAMP,
            NULL::TIMESTAMP,
            NULL::INTEGER,
            NULL::VARCHAR,
            NULL::JSONB;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FORCE RELEASE LOCK FUNCTION (ADMIN)
-- ============================================================================
CREATE OR REPLACE FUNCTION force_release_lock(
    p_resource_id VARCHAR,
    p_admin_agent_id VARCHAR DEFAULT 'admin'
)
RETURNS TABLE(
    success BOOLEAN,
    message TEXT,
    previous_owner VARCHAR
) AS $$
DECLARE
    v_lock_key BIGINT;
    v_owner VARCHAR;
BEGIN
    v_lock_key := resource_id_to_lock_key(p_resource_id);
    
    -- Get current owner
    SELECT agent_id INTO v_owner
    FROM resource_locks
    WHERE resource_id = p_resource_id;
    
    IF v_owner IS NOT NULL THEN
        -- Force release
        PERFORM pg_advisory_unlock(v_lock_key);
        DELETE FROM resource_locks WHERE resource_id = p_resource_id;
        DELETE FROM lock_wait_queue WHERE resource_id = p_resource_id;
        
        -- Log force release
        INSERT INTO lock_history (
            resource_id, agent_id, operation, success, error_message
        ) VALUES (
            p_resource_id, p_admin_agent_id, 'force_release', TRUE,
            'Forced release from: ' || v_owner
        );
        
        RETURN QUERY SELECT TRUE, 'Lock forcefully released'::TEXT, v_owner;
    ELSE
        RETURN QUERY SELECT FALSE, 'Lock not found'::TEXT, NULL::VARCHAR;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CLEANUP EXPIRED LOCKS FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_expired_locks()
RETURNS TABLE(
    cleaned_count INTEGER,
    resource_ids TEXT[]
) AS $$
DECLARE
    v_expired_locks RECORD;
    v_count INTEGER := 0;
    v_resource_ids TEXT[] := ARRAY[]::TEXT[];
BEGIN
    FOR v_expired_locks IN 
        SELECT resource_id, agent_id, lock_key
        FROM resource_locks
        WHERE expires_at < NOW()
    LOOP
        -- Release advisory lock
        PERFORM pg_advisory_unlock(v_expired_locks.lock_key);
        
        -- Log timeout
        INSERT INTO lock_history (
            resource_id, agent_id, operation, success, error_message
        ) VALUES (
            v_expired_locks.resource_id,
            v_expired_locks.agent_id,
            'timeout',
            FALSE,
            'Lock expired and auto-released'
        );
        
        v_count := v_count + 1;
        v_resource_ids := array_append(v_resource_ids, v_expired_locks.resource_id);
    END LOOP;
    
    -- Delete expired locks
    DELETE FROM resource_locks WHERE expires_at < NOW();
    
    -- Clean up expired wait queue entries
    DELETE FROM lock_wait_queue WHERE timeout_at < NOW();
    
    RETURN QUERY SELECT v_count, v_resource_ids;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- AUTO-CLEANUP TRIGGER
-- ============================================================================
CREATE OR REPLACE FUNCTION trigger_cleanup_expired_locks()
RETURNS TRIGGER AS $$
BEGIN
    -- Run cleanup on any lock operation
    PERFORM cleanup_expired_locks();
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS auto_cleanup_expired_locks ON resource_locks;
CREATE TRIGGER auto_cleanup_expired_locks
    AFTER INSERT OR UPDATE ON resource_locks
    EXECUTE FUNCTION trigger_cleanup_expired_locks();

-- ============================================================================
-- MONITORING VIEWS
-- ============================================================================

-- Active locks view
CREATE OR REPLACE VIEW active_locks_view AS
SELECT 
    rl.resource_id,
    rl.agent_id,
    rl.acquired_at,
    rl.expires_at,
    EXTRACT(EPOCH FROM (NOW() - rl.acquired_at))::INTEGER as held_seconds,
    EXTRACT(EPOCH FROM (rl.expires_at - NOW()))::INTEGER as remaining_seconds,
    rl.reason,
    rl.metadata,
    (SELECT COUNT(*) FROM lock_wait_queue WHERE resource_id = rl.resource_id) as waiting_count
FROM resource_locks rl
WHERE rl.expires_at > NOW()
ORDER BY rl.acquired_at;

-- Lock statistics view
CREATE OR REPLACE VIEW lock_statistics_view AS
SELECT 
    resource_id,
    COUNT(*) FILTER (WHERE success = TRUE) as successful_acquisitions,
    COUNT(*) FILTER (WHERE success = FALSE) as failed_acquisitions,
    AVG(wait_time_ms) FILTER (WHERE success = TRUE) as avg_wait_time_ms,
    MAX(wait_time_ms) as max_wait_time_ms,
    AVG(duration_ms) FILTER (WHERE operation = 'release') as avg_hold_time_ms,
    MAX(duration_ms) FILTER (WHERE operation = 'release') as max_hold_time_ms,
    COUNT(DISTINCT agent_id) as unique_agents,
    MAX(created_at) as last_operation
FROM lock_history
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY resource_id
ORDER BY successful_acquisitions DESC;

-- Lock contention view
CREATE OR REPLACE VIEW lock_contention_view AS
SELECT 
    lh.resource_id,
    COUNT(*) as contention_events,
    COUNT(DISTINCT lh.agent_id) as competing_agents,
    AVG(lh.wait_time_ms) as avg_wait_time_ms,
    MAX(lh.wait_time_ms) as max_wait_time_ms,
    (SELECT COUNT(*) FROM lock_wait_queue WHERE resource_id = lh.resource_id) as current_queue_depth
FROM lock_history lh
WHERE lh.success = FALSE
AND lh.operation = 'acquire'
AND lh.created_at > NOW() - INTERVAL '1 hour'
GROUP BY lh.resource_id
ORDER BY contention_events DESC;

-- Wait queue view
CREATE OR REPLACE VIEW wait_queue_view AS
SELECT 
    lwq.resource_id,
    lwq.agent_id,
    lwq.requested_at,
    lwq.timeout_at,
    EXTRACT(EPOCH FROM (NOW() - lwq.requested_at))::INTEGER as waiting_seconds,
    EXTRACT(EPOCH FROM (lwq.timeout_at - NOW()))::INTEGER as remaining_timeout_seconds,
    lwq.priority,
    (SELECT agent_id FROM resource_locks WHERE resource_id = lwq.resource_id) as current_owner
FROM lock_wait_queue lwq
ORDER BY lwq.priority DESC, lwq.requested_at;

-- ============================================================================
-- MAINTENANCE QUERIES
-- ============================================================================

-- Run periodic cleanup (add to cron or scheduled task)
-- SELECT * FROM cleanup_expired_locks();

-- Check active locks
-- SELECT * FROM active_locks_view;

-- Check lock contention
-- SELECT * FROM lock_contention_view WHERE contention_events > 5;

-- Check wait queue
-- SELECT * FROM wait_queue_view;

-- View lock statistics
-- SELECT * FROM lock_statistics_view;

-- ============================================================================
-- Agent Registry Database Schema
-- ============================================================================
-- Purpose: Store agent registrations, capabilities, and health status
-- Part of: Phase 6 - Multi-Agent Collaboration
-- ============================================================================

-- Agent Registry Table
CREATE TABLE IF NOT EXISTS agent_registry (
    -- Identity
    agent_id VARCHAR(64) PRIMARY KEY,
    agent_name VARCHAR(128) NOT NULL,
    base_url VARCHAR(256) NOT NULL,
    
    -- Status
    status VARCHAR(32) NOT NULL DEFAULT 'active',  -- active, busy, offline
    
    -- Capabilities (JSONB array of capability objects)
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    last_heartbeat TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_status 
    ON agent_registry(status);

CREATE INDEX IF NOT EXISTS idx_agent_heartbeat 
    ON agent_registry(last_heartbeat);

CREATE INDEX IF NOT EXISTS idx_agent_capabilities 
    ON agent_registry USING GIN(capabilities);

CREATE INDEX IF NOT EXISTS idx_agent_updated 
    ON agent_registry(updated_at);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_agent_registry_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_agent_registry_timestamp
    BEFORE UPDATE ON agent_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_registry_timestamp();

-- ============================================================================
-- Views
-- ============================================================================

-- Active agents view
CREATE OR REPLACE VIEW active_agents AS
SELECT 
    agent_id,
    agent_name,
    base_url,
    capabilities,
    last_heartbeat,
    EXTRACT(EPOCH FROM (NOW() - last_heartbeat))::INT AS seconds_since_heartbeat
FROM agent_registry
WHERE status = 'active'
ORDER BY agent_name;

-- Stale agents view (no heartbeat in 60+ seconds)
CREATE OR REPLACE VIEW stale_agents AS
SELECT 
    agent_id,
    agent_name,
    base_url,
    status,
    last_heartbeat,
    EXTRACT(EPOCH FROM (NOW() - last_heartbeat))::INT AS seconds_since_heartbeat
FROM agent_registry
WHERE last_heartbeat < NOW() - INTERVAL '60 seconds'
ORDER BY last_heartbeat;

-- Agent capabilities flattened view
CREATE OR REPLACE VIEW agent_capabilities_flat AS
SELECT 
    agent_id,
    agent_name,
    base_url,
    status,
    capability->>'name' AS capability_name,
    capability->>'description' AS capability_description,
    capability->'tags' AS capability_tags,
    capability->>'cost_estimate' AS cost_estimate
FROM agent_registry,
     jsonb_array_elements(capabilities) AS capability
WHERE status = 'active';

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Search capabilities by keyword
CREATE OR REPLACE FUNCTION search_capabilities(search_term TEXT)
RETURNS TABLE (
    agent_id VARCHAR(64),
    agent_name VARCHAR(128),
    capability_name TEXT,
    capability_description TEXT,
    base_url VARCHAR(256)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ar.agent_id,
        ar.agent_name,
        cap.capability_name,
        cap.capability_description,
        ar.base_url
    FROM agent_registry ar,
         agent_capabilities_flat cap
    WHERE ar.agent_id = cap.agent_id
      AND ar.status = 'active'
      AND (
          LOWER(cap.capability_name) LIKE '%' || LOWER(search_term) || '%'
          OR LOWER(cap.capability_description) LIKE '%' || LOWER(search_term) || '%'
      );
END;
$$ LANGUAGE plpgsql;

-- Get agent by capability
CREATE OR REPLACE FUNCTION get_agent_by_capability(capability_name TEXT)
RETURNS TABLE (
    agent_id VARCHAR(64),
    agent_name VARCHAR(128),
    base_url VARCHAR(256),
    capability_description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ar.agent_id,
        ar.agent_name,
        ar.base_url,
        cap.capability_description
    FROM agent_registry ar,
         agent_capabilities_flat cap
    WHERE ar.agent_id = cap.agent_id
      AND ar.status = 'active'
      AND cap.capability_name = get_agent_by_capability.capability_name
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Sample Data (for testing)
-- ============================================================================

-- Note: Agents will auto-register on startup, but here's example data for testing

-- INSERT INTO agent_registry (agent_id, agent_name, base_url, status, capabilities) VALUES
-- ('orchestrator', 'Orchestrator Agent', 'http://orchestrator:8001', 'active', 
--  '[{"name": "orchestrate_task", "description": "Decompose and route complex tasks", "parameters": {"task": "str"}, "cost_estimate": "~50 tokens", "tags": ["coordination", "routing"]}]'::jsonb
-- ),
-- ('code-review', 'Code Review Agent', 'http://code-review:8003', 'active',
--  '[{"name": "review_pr", "description": "Review pull request for code quality", "parameters": {"repo_url": "str", "pr_number": "int"}, "cost_estimate": "~100 tokens", "tags": ["git", "security", "code-quality"]}]'::jsonb
-- ),
-- ('feature-dev', 'Feature Development Agent', 'http://feature-dev:8002', 'active',
--  '[{"name": "implement_feature", "description": "Implement new feature from specification", "parameters": {"spec": "str"}, "cost_estimate": "~200 tokens", "tags": ["development", "coding"]}]'::jsonb
-- ),
-- ('infrastructure', 'Infrastructure Agent', 'http://infrastructure:8004', 'active',
--  '[{"name": "deploy_service", "description": "Deploy service to environment", "parameters": {"service": "str", "environment": "str"}, "cost_estimate": "~30s compute", "tags": ["deployment", "infrastructure"]}]'::jsonb
-- ),
-- ('cicd', 'CI/CD Agent', 'http://cicd:8005', 'active',
--  '[{"name": "run_tests", "description": "Run test suite for repository", "parameters": {"repo_url": "str", "commit_sha": "str"}, "cost_estimate": "~60s compute", "tags": ["testing", "ci"]}]'::jsonb
-- ),
-- ('documentation', 'Documentation Agent', 'http://documentation:8006', 'active',
--  '[{"name": "generate_docs", "description": "Generate documentation from code", "parameters": {"repo_url": "str"}, "cost_estimate": "~150 tokens", "tags": ["documentation", "generation"]}]'::jsonb
-- );

-- ============================================================================
-- Analytics Queries
-- ============================================================================

-- Agent health summary
-- SELECT 
--     status,
--     COUNT(*) AS count,
--     AVG(EXTRACT(EPOCH FROM (NOW() - last_heartbeat)))::INT AS avg_seconds_since_heartbeat
-- FROM agent_registry
-- GROUP BY status;

-- Capability distribution
-- SELECT 
--     capability_name,
--     COUNT(*) AS agent_count
-- FROM agent_capabilities_flat
-- GROUP BY capability_name
-- ORDER BY agent_count DESC;

-- Most active agents (by recent heartbeat)
-- SELECT 
--     agent_id,
--     agent_name,
--     last_heartbeat,
--     EXTRACT(EPOCH FROM (NOW() - last_heartbeat))::INT AS seconds_since_heartbeat
-- FROM agent_registry
-- WHERE status = 'active'
-- ORDER BY last_heartbeat DESC
-- LIMIT 10;

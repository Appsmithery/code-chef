-- Task to Linear Issue Mappings (Phase 5)
-- 
-- Stores mapping between orchestrator task IDs and agent-created Linear sub-issues
-- Enables agents to update Linear issues as tasks progress

CREATE TABLE IF NOT EXISTS task_linear_mappings (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    linear_issue_id VARCHAR(255) NOT NULL,
    linear_identifier VARCHAR(50) NOT NULL,  -- e.g., "PR-123"
    agent_name VARCHAR(50) NOT NULL,
    parent_issue_id VARCHAR(255),  -- Parent Linear issue (approval/orchestrator task)
    parent_identifier VARCHAR(50),  -- e.g., "PR-68"
    status VARCHAR(50) DEFAULT 'todo',  -- todo, in_progress, done, canceled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Indexes for fast lookups
    INDEX idx_task_id (task_id),
    INDEX idx_linear_issue_id (linear_issue_id),
    INDEX idx_agent_name (agent_name),
    INDEX idx_status (status)
);

-- Trigger to update updated_at on row modification
CREATE OR REPLACE FUNCTION update_task_mapping_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_linear_mappings_update
    BEFORE UPDATE ON task_linear_mappings
    FOR EACH ROW
    EXECUTE FUNCTION update_task_mapping_timestamp();

-- Example queries:

-- Find Linear issue for task
-- SELECT linear_issue_id, linear_identifier, status 
-- FROM task_linear_mappings 
-- WHERE task_id = 'abc123-def456';

-- Find all sub-issues for parent
-- SELECT task_id, linear_identifier, agent_name, status
-- FROM task_linear_mappings
-- WHERE parent_identifier = 'DEV-68'
-- ORDER BY created_at DESC;

-- Get agent's active tasks
-- SELECT task_id, linear_identifier, created_at
-- FROM task_linear_mappings
-- WHERE agent_name = 'feature-dev' AND status = 'in_progress';

-- Task completion rate by agent
-- SELECT 
--     agent_name,
--     COUNT(*) as total_tasks,
--     SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
--     ROUND(100.0 * SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) / COUNT(*), 2) as completion_rate
-- FROM task_linear_mappings
-- GROUP BY agent_name;

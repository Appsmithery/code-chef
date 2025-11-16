-- LangGraph PostgreSQL Checkpointing Schema
-- Extends the existing devtools database with LangGraph checkpoint tables

-- Create checkpoint schema for LangGraph
CREATE SCHEMA IF NOT EXISTS checkpoints;

-- Main checkpoint table
CREATE TABLE IF NOT EXISTS checkpoints.checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- Index for efficient parent lookups
CREATE INDEX IF NOT EXISTS idx_checkpoints_parent 
ON checkpoints.checkpoints(parent_checkpoint_id);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_checkpoints_created 
ON checkpoints.checkpoints(created_at DESC);

-- Checkpoint writes table for tracking state transitions
CREATE TABLE IF NOT EXISTS checkpoints.checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (thread_id, checkpoint_id) 
        REFERENCES checkpoints.checkpoints(thread_id, checkpoint_id) 
        ON DELETE CASCADE
);

-- Index for efficient write lookups
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_lookup 
ON checkpoints.checkpoint_writes(thread_id, checkpoint_id);

-- Checkpoint metadata table for additional tracking
CREATE TABLE IF NOT EXISTS checkpoints.checkpoint_metadata (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_id, key),
    FOREIGN KEY (thread_id, checkpoint_id) 
        REFERENCES checkpoints.checkpoints(thread_id, checkpoint_id) 
        ON DELETE CASCADE
);

-- Create view for latest checkpoints per thread
CREATE OR REPLACE VIEW checkpoints.latest_checkpoints AS
SELECT DISTINCT ON (thread_id)
    thread_id,
    checkpoint_id,
    parent_checkpoint_id,
    checkpoint,
    metadata,
    created_at
FROM checkpoints.checkpoints
ORDER BY thread_id, created_at DESC;

-- Grant permissions (adjust as needed for your setup)
GRANT USAGE ON SCHEMA checkpoints TO devtools;
GRANT ALL ON ALL TABLES IN SCHEMA checkpoints TO devtools;
GRANT ALL ON ALL SEQUENCES IN SCHEMA checkpoints TO devtools;

-- Comments for documentation
COMMENT ON SCHEMA checkpoints IS 'LangGraph checkpoint storage for workflow state persistence';
COMMENT ON TABLE checkpoints.checkpoints IS 'Main checkpoint table storing workflow states';
COMMENT ON TABLE checkpoints.checkpoint_writes IS 'Individual state write operations within checkpoints';
COMMENT ON TABLE checkpoints.checkpoint_metadata IS 'Additional metadata for checkpoint tracking';
COMMENT ON VIEW checkpoints.latest_checkpoints IS 'Latest checkpoint for each workflow thread';

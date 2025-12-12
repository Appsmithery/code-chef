-- Approval Requests Table for HITL Workflows
-- Stores workflow approval state and history

CREATE TABLE IF NOT EXISTS approval_requests (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),
    checkpoint_id VARCHAR(255),
    
    -- Task details
    task_type VARCHAR(100),
    task_description TEXT NOT NULL,
    
    -- Agent context
    agent_name VARCHAR(100) NOT NULL,
    
    -- Risk assessment
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    risk_score FLOAT,
    risk_factors JSONB DEFAULT '{}',
    
    -- Action details
    action_type VARCHAR(100),
    action_details JSONB DEFAULT '{}',
    action_impact TEXT,
    
    -- Approval workflow
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')),
    
    -- Approver details
    approver_id VARCHAR(100),
    approver_role VARCHAR(50),
    approved_at TIMESTAMP,
    rejected_at TIMESTAMP,
    rejection_reason TEXT,
    approval_justification TEXT,
    
    -- Workflow resumption
    resumed_at TIMESTAMP,
    
    -- Timeout handling
    expires_at TIMESTAMP,
    
    -- Audit trail
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Linear integration
    linear_issue_id VARCHAR(100),
    linear_issue_url TEXT,
    
    -- GitHub integration (Phase 2)
    pr_number INTEGER,
    pr_url TEXT,
    github_repo VARCHAR(255)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_workflow ON approval_requests(workflow_id);
CREATE INDEX IF NOT EXISTS idx_approval_created_at ON approval_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_approval_risk_level ON approval_requests(risk_level);
CREATE INDEX IF NOT EXISTS idx_approval_expires ON approval_requests(expires_at) WHERE status = 'pending';

-- Approval Actions Table (audit trail of individual approvals/rejections)
CREATE TABLE IF NOT EXISTS approval_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    
    -- Action details
    action VARCHAR(20) NOT NULL CHECK (action IN ('approve', 'reject', 'escalate', 'timeout')),
    actor VARCHAR(100) NOT NULL,
    actor_role VARCHAR(50),
    
    -- Justification
    note TEXT,
    justification TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_approval_actions_request ON approval_actions(approval_request_id);
CREATE INDEX IF NOT EXISTS idx_approval_actions_actor ON approval_actions(actor);
CREATE INDEX IF NOT EXISTS idx_approval_actions_created ON approval_actions(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_approval_requests_updated_at
    BEFORE UPDATE ON approval_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for pending approvals (commonly used query)
CREATE OR REPLACE VIEW pending_approvals AS
SELECT 
    ar.id,
    ar.workflow_id,
    ar.thread_id,
    ar.checkpoint_id,
    ar.task_type,
    ar.task_description,
    ar.agent_name,
    ar.risk_level,
    ar.risk_score,
    ar.action_type,
    ar.action_impact,
    ar.created_at,
    ar.expires_at,
    EXTRACT(EPOCH FROM (ar.expires_at - NOW())) / 60 AS minutes_remaining
FROM approval_requests ar
WHERE ar.status = 'pending' AND ar.expires_at > NOW()
ORDER BY 
    CASE ar.risk_level
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    ar.created_at ASC;

-- View for approval statistics
CREATE OR REPLACE VIEW approval_statistics AS
SELECT 
    DATE_TRUNC('day', created_at) AS day,
    risk_level,
    status,
    COUNT(*) AS count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(approved_at, rejected_at) - created_at)) / 60) AS avg_resolution_minutes
FROM approval_requests
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), risk_level, status
ORDER BY day DESC, risk_level;

-- Comments for documentation
COMMENT ON TABLE approval_requests IS 'Stores HITL approval requests for high-risk autonomous operations';
COMMENT ON TABLE approval_actions IS 'Audit trail of all approval/rejection actions';
COMMENT ON VIEW pending_approvals IS 'Active approvals awaiting decision, ordered by priority';
COMMENT ON VIEW approval_statistics IS 'Historical approval metrics for the past 30 days';

-- Grant permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE ON approval_requests TO devtools;
GRANT SELECT, INSERT ON approval_actions TO devtools;
GRANT SELECT ON pending_approvals TO devtools;
GRANT SELECT ON approval_statistics TO devtools;

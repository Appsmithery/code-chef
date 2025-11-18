-- Approval Requests Table for HITL Workflows
-- Stores workflow approval state and history

CREATE TABLE IF NOT EXISTS approval_requests (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    
    -- Risk assessment
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    operation_type VARCHAR(100),
    
    -- Request details
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Approval workflow
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'timeout', 'canceled')),
    requested_by VARCHAR(100) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Approvers
    approvers TEXT[] NOT NULL,  -- Array of role names
    required_approvals INTEGER DEFAULT 1,
    received_approvals INTEGER DEFAULT 0,
    
    -- Timeout handling
    timeout_at TIMESTAMP,
    timeout_minutes INTEGER DEFAULT 30,
    escalated BOOLEAN DEFAULT FALSE,
    escalation_count INTEGER DEFAULT 0,
    
    -- Resolution
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMP,
    resolution_note TEXT,
    approval_justification TEXT,
    
    -- Audit trail
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT unique_workflow_task UNIQUE (workflow_id, task_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_workflow ON approval_requests(workflow_id);
CREATE INDEX IF NOT EXISTS idx_approval_requested_at ON approval_requests(requested_at);
CREATE INDEX IF NOT EXISTS idx_approval_risk_level ON approval_requests(risk_level);
CREATE INDEX IF NOT EXISTS idx_approval_timeout ON approval_requests(timeout_at) WHERE status = 'pending';

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
    ar.task_id,
    ar.risk_level,
    ar.operation_type,
    ar.description,
    ar.requested_by,
    ar.requested_at,
    ar.approvers,
    ar.timeout_at,
    ar.escalated,
    ar.escalation_count,
    EXTRACT(EPOCH FROM (ar.timeout_at - NOW())) / 60 AS minutes_remaining
FROM approval_requests ar
WHERE ar.status = 'pending'
ORDER BY 
    CASE ar.risk_level
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    ar.requested_at ASC;

-- View for approval statistics
CREATE OR REPLACE VIEW approval_statistics AS
SELECT 
    DATE_TRUNC('day', requested_at) AS day,
    risk_level,
    status,
    COUNT(*) AS count,
    AVG(EXTRACT(EPOCH FROM (resolved_at - requested_at)) / 60) AS avg_resolution_minutes
FROM approval_requests
WHERE requested_at > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', requested_at), risk_level, status
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

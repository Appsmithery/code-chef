-- Evaluation Results Schema - Longitudinal Performance Tracking
-- Supports A/B testing (baseline vs code-chef) and time-series analysis
-- Part of Phase 1: Testing, Tracing & Evaluation Refactoring (CHEF-239)

-- Main evaluation results table with time-series optimization
CREATE TABLE IF NOT EXISTS evaluation_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Experiment correlation
    experiment_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    experiment_group VARCHAR(20) NOT NULL CHECK (experiment_group IN ('baseline', 'code-chef')),
    
    -- Version tracking for longitudinal analysis
    extension_version VARCHAR(50) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    
    -- Agent context
    agent_name VARCHAR(100),
    
    -- Evaluation scores (from evaluators.py)
    accuracy FLOAT CHECK (accuracy >= 0 AND accuracy <= 1),
    completeness FLOAT CHECK (completeness >= 0 AND completeness <= 1),
    efficiency FLOAT CHECK (efficiency >= 0 AND efficiency <= 1),
    integration_quality FLOAT CHECK (integration_quality >= 0 AND integration_quality <= 1),
    
    -- Performance metrics
    latency_ms FLOAT CHECK (latency_ms >= 0),
    tokens_used INTEGER CHECK (tokens_used >= 0),
    cost_usd FLOAT CHECK (cost_usd >= 0),
    
    -- Execution metadata
    execution_time_seconds FLOAT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    
    -- Timestamps (critical for time-series queries)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Additional context
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Ensure unique results per experiment+task+group+version
    UNIQUE (experiment_id, task_id, experiment_group, extension_version)
);

-- Time-series indexes for longitudinal queries
CREATE INDEX IF NOT EXISTS idx_eval_results_created_at ON evaluation_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_eval_results_version_time ON evaluation_results(extension_version, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_eval_results_agent_time ON evaluation_results(agent_name, created_at DESC) WHERE agent_name IS NOT NULL;

-- Experiment correlation indexes
CREATE INDEX IF NOT EXISTS idx_eval_results_experiment ON evaluation_results(experiment_id, task_id);
CREATE INDEX IF NOT EXISTS idx_eval_results_group ON evaluation_results(experiment_group, experiment_id);

-- Performance query indexes
CREATE INDEX IF NOT EXISTS idx_eval_results_metrics ON evaluation_results(agent_name, experiment_group, extension_version);

-- Optional: Enable TimescaleDB hypertable for advanced time-series features
-- Uncomment if TimescaleDB extension is installed:
-- SELECT create_hypertable('evaluation_results', 'created_at', if_not_exists => TRUE);

-- Correlation table to link baseline and code-chef runs
CREATE TABLE IF NOT EXISTS task_comparisons (
    comparison_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Experiment metadata
    experiment_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    
    -- LangSmith run IDs for traceability
    baseline_run_id VARCHAR(255),
    codechef_run_id VARCHAR(255),
    
    -- Quick access to results
    baseline_result_id UUID REFERENCES evaluation_results(result_id) ON DELETE CASCADE,
    codechef_result_id UUID REFERENCES evaluation_results(result_id) ON DELETE CASCADE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Metadata (task prompt, expected outcome, etc.)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    UNIQUE (experiment_id, task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_comparisons_experiment ON task_comparisons(experiment_id);
CREATE INDEX IF NOT EXISTS idx_task_comparisons_baseline ON task_comparisons(baseline_run_id);
CREATE INDEX IF NOT EXISTS idx_task_comparisons_codechef ON task_comparisons(codechef_run_id);

-- Experiment summaries for cacheable aggregate results
CREATE TABLE IF NOT EXISTS experiment_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Experiment identification
    experiment_id VARCHAR(255) UNIQUE NOT NULL,
    experiment_name VARCHAR(255),
    
    -- A/B comparison results
    total_tasks INTEGER NOT NULL CHECK (total_tasks >= 0),
    codechef_wins INTEGER NOT NULL DEFAULT 0 CHECK (codechef_wins >= 0),
    baseline_wins INTEGER NOT NULL DEFAULT 0 CHECK (baseline_wins >= 0),
    ties INTEGER NOT NULL DEFAULT 0 CHECK (ties >= 0),
    
    -- Aggregate improvement metrics (positive = code-chef better)
    avg_accuracy_improvement_pct FLOAT,
    avg_latency_reduction_pct FLOAT,
    avg_cost_reduction_pct FLOAT,
    avg_completeness_improvement_pct FLOAT,
    
    -- Statistical validation (for future use)
    statistical_significance FLOAT,  -- p-value
    
    -- Execution metadata
    completed_at TIMESTAMPTZ,
    computation_time_seconds FLOAT,
    
    -- Detailed breakdown
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiment_summaries_completed ON experiment_summaries(completed_at DESC) WHERE completed_at IS NOT NULL;

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_experiment_summaries_updated_at BEFORE UPDATE ON experiment_summaries
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for quick A/B comparison queries
CREATE OR REPLACE VIEW evaluation_comparison_view AS
SELECT 
    er.experiment_id,
    er.task_id,
    er.agent_name,
    er.extension_version,
    
    -- Baseline metrics
    MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.accuracy END) as baseline_accuracy,
    MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.latency_ms END) as baseline_latency_ms,
    MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.cost_usd END) as baseline_cost_usd,
    MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.completeness END) as baseline_completeness,
    
    -- Code-chef metrics
    MAX(CASE WHEN er.experiment_group = 'code-chef' THEN er.accuracy END) as codechef_accuracy,
    MAX(CASE WHEN er.experiment_group = 'code-chef' THEN er.latency_ms END) as codechef_latency_ms,
    MAX(CASE WHEN er.experiment_group = 'code-chef' THEN er.cost_usd END) as codechef_cost_usd,
    MAX(CASE WHEN er.experiment_group = 'code-chef' THEN er.completeness END) as codechef_completeness,
    
    -- Improvement calculations
    (MAX(CASE WHEN er.experiment_group = 'code-chef' THEN er.accuracy END) - 
     MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.accuracy END)) * 100 as accuracy_improvement_pct,
    
    (MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.latency_ms END) - 
     MAX(CASE WHEN er.experiment_group = 'code-chef' THEN er.latency_ms END)) / 
     NULLIF(MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.latency_ms END), 0) * 100 as latency_reduction_pct,
    
    (MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.cost_usd END) - 
     MAX(CASE WHEN er.experiment_group = 'code-chef' THEN er.cost_usd END)) / 
     NULLIF(MAX(CASE WHEN er.experiment_group = 'baseline' THEN er.cost_usd END), 0) * 100 as cost_reduction_pct,
    
    er.created_at
FROM evaluation_results er
GROUP BY er.experiment_id, er.task_id, er.agent_name, er.extension_version, er.created_at
HAVING COUNT(DISTINCT er.experiment_group) = 2;  -- Only show tasks with both baseline and code-chef results

COMMENT ON VIEW evaluation_comparison_view IS 'Quick A/B comparison view showing baseline vs code-chef metrics side-by-side with improvement percentages';

-- Cleanup function for old evaluation results (data retention)
CREATE OR REPLACE FUNCTION cleanup_old_evaluation_results(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM evaluation_results 
    WHERE created_at < NOW() - INTERVAL '1 day' * retention_days
    AND metadata->>'archive' IS DISTINCT FROM 'true';  -- Don't delete archived results
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_evaluation_results IS 'Delete evaluation results older than retention_days (default 90), excluding archived results';

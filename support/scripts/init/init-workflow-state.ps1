#!/usr/bin/env pwsh
# Initialize workflow state tables in PostgreSQL
# Usage: .\support\scripts\init-workflow-state.ps1

Write-Host "Initializing workflow state tables..." -ForegroundColor Cyan

# Get database connection details (PowerShell 5.1 compatible)
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "devtools" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "devtools" }
$DB_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "changeme" }

$SCHEMA_FILE = "config/state/workflow_state.sql"

if (-not (Test-Path $SCHEMA_FILE)) {
    Write-Host "Error: Schema file not found: $SCHEMA_FILE" -ForegroundColor Red
    exit 1
}

Write-Host "Database: ${DB_HOST}:${DB_PORT}/${DB_NAME}" -ForegroundColor Gray
Write-Host "Schema file: $SCHEMA_FILE" -ForegroundColor Gray

# Check if psql is available
$psqlAvailable = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlAvailable) {
    Write-Host "Warning: psql not found. Using docker exec instead..." -ForegroundColor Yellow
    
    # Execute via docker
    $containerName = "deploy-postgres-1"
    Write-Host "Executing via container: $containerName" -ForegroundColor Gray
    
    Get-Content $SCHEMA_FILE | docker exec -i $containerName psql -U $DB_USER -d $DB_NAME
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Workflow state tables initialized successfully!" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to initialize tables (exit code: $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} else {
    # Execute directly with psql
    $env:PGPASSWORD = $DB_PASSWORD
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $SCHEMA_FILE
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Workflow state tables initialized successfully!" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to initialize tables (exit code: $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Verify tables created
Write-Host "`nVerifying tables..." -ForegroundColor Cyan

$verifyQuery = @"
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('workflow_state', 'workflow_checkpoints', 'langgraph_checkpoints', 'langgraph_writes')
ORDER BY table_name;
"@

if (-not $psqlAvailable) {
    $tables = docker exec -i $containerName psql -U $DB_USER -d $DB_NAME -t -c $verifyQuery
} else {
    $env:PGPASSWORD = $DB_PASSWORD
    $tables = psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c $verifyQuery
}

if ($tables) {
    Write-Host "Tables created:" -ForegroundColor Green
    $tables -split "`n" | Where-Object { $_.Trim() } | ForEach-Object {
        Write-Host "  - $($_.Trim())" -ForegroundColor Green
    }
} else {
    Write-Host "Warning: Could not verify table creation" -ForegroundColor Yellow
}

Write-Host "`n✓ Initialization complete!" -ForegroundColor Green
Write-Host "Ready for multi-agent workflow execution." -ForegroundColor Gray

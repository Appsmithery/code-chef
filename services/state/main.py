"""
State Persistence Layer Service

Manages task state, workflow tracking, and agent logs in PostgreSQL.
Provides CRUD operations for orchestrator and agent state management.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import os
import json

app = FastAPI(title="State Persistence Layer", version="1.0.0")

# PostgreSQL connection configuration
PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB", "devtools")
PG_USER = os.getenv("POSTGRES_USER", "admin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")


def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


# Request/Response Models
class TaskCreate(BaseModel):
    """Create new task"""
    task_id: str
    type: str
    status: str = "pending"
    assigned_agent: Optional[str] = None
    payload: Dict[str, Any]


class TaskUpdate(BaseModel):
    """Update existing task"""
    status: Optional[str] = None
    assigned_agent: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class Task(BaseModel):
    """Task representation"""
    id: int
    task_id: str
    type: str
    status: str
    assigned_agent: Optional[str]
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class AgentLogCreate(BaseModel):
    """Create agent log entry"""
    task_id: str
    agent: str
    log_level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class AgentLog(BaseModel):
    """Agent log entry"""
    id: int
    task_id: str
    agent: str
    log_level: str
    message: str
    metadata: Optional[Dict[str, Any]]
    timestamp: datetime


class WorkflowCreate(BaseModel):
    """Create workflow"""
    workflow_id: str
    name: str
    steps: List[Dict[str, Any]]
    status: str = "pending"


class WorkflowUpdate(BaseModel):
    """Update workflow"""
    status: Optional[str] = None
    completed_at: Optional[datetime] = None


class Workflow(BaseModel):
    """Workflow representation"""
    id: int
    workflow_id: str
    name: str
    steps: List[Dict[str, Any]]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]


# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    conn = get_db_connection()
    db_status = "connected" if conn else "disconnected"
    if conn:
        conn.close()
    
    return {
        "status": "ok",
        "service": "state-persistence",
        "version": "1.0.0",
        "database_status": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


# Initialize database schema
@app.post("/init")
async def initialize_schema():
    """Initialize database schema from schema.sql"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        # Read schema file
        schema_path = "/app/schema.sql"
        if not os.path.exists(schema_path):
            schema_path = "../../configs/state/schema.sql"
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Database schema initialized successfully"
        }
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Schema initialization failed: {str(e)}")


# Task endpoints
@app.post("/tasks", response_model=Task)
async def create_task(task: TaskCreate):
    """Create new task"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (task_id, type, status, assigned_agent, payload, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING *
            """,
            (task.task_id, task.type, task.status, task.assigned_agent, Json(task.payload))
        )
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return Task(**result)
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """Get task by ID"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = %s", (task_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return Task(**result)
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Task retrieval failed: {str(e)}")


@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, update: TaskUpdate):
    """Update task"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        
        # Build update query dynamically
        updates = []
        values = []
        
        if update.status:
            updates.append("status = %s")
            values.append(update.status)
        if update.assigned_agent:
            updates.append("assigned_agent = %s")
            values.append(update.assigned_agent)
        if update.result:
            updates.append("result = %s")
            values.append(Json(update.result))
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = %s RETURNING *"
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return Task(**result)
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Task update failed: {str(e)}")


@app.get("/tasks", response_model=List[Task])
async def list_tasks(status: Optional[str] = None, limit: int = 100):
    """List tasks with optional status filter"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM tasks WHERE status = %s ORDER BY created_at DESC LIMIT %s",
                (status, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [Task(**row) for row in results]
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Task listing failed: {str(e)}")


# Agent log endpoints
@app.post("/logs", response_model=AgentLog)
async def create_log(log: AgentLogCreate):
    """Create agent log entry"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO agent_logs (task_id, agent, log_level, message, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (log.task_id, log.agent, log.log_level, log.message, Json(log.metadata) if log.metadata else None)
        )
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return AgentLog(**result)
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Log creation failed: {str(e)}")


@app.get("/logs/{task_id}", response_model=List[AgentLog])
async def get_task_logs(task_id: str):
    """Get all logs for a task"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM agent_logs WHERE task_id = %s ORDER BY timestamp ASC",
            (task_id,)
        )
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [AgentLog(**row) for row in results]
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Log retrieval failed: {str(e)}")


# Workflow endpoints
@app.post("/workflows", response_model=Workflow)
async def create_workflow(workflow: WorkflowCreate):
    """Create workflow"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO workflows (workflow_id, name, steps, status)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (workflow.workflow_id, workflow.name, Json(workflow.steps), workflow.status)
        )
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return Workflow(**result)
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Workflow creation failed: {str(e)}")


@app.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    """Get workflow by ID"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workflows WHERE workflow_id = %s", (workflow_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return Workflow(**result)
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Workflow retrieval failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)

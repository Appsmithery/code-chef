"""
Code Review Agent

Primary Role: Quality assurance, static analysis, and security scanning
- Performs static code analysis on diffs (not full codebases)
- Executes security vulnerability scanning and dependency checks
- Validates coding standards compliance and best practices
- Reviews test coverage and test quality metrics
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
import uvicorn
import os

app = FastAPI(
    title="Code Review Agent",
    description="Quality assurance, static analysis, and security scanning",
    version="1.0.0"
)

class CodeDiff(BaseModel):
    file_path: str
    changes: str
    context_lines: int = 5

class ReviewRequest(BaseModel):
    task_id: str
    diffs: List[CodeDiff]
    test_results: Optional[Dict[str, Any]] = None

class ReviewFinding(BaseModel):
    severity: str
    category: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None

class ReviewResponse(BaseModel):
    review_id: str
    status: str
    findings: List[ReviewFinding]
    approval: bool
    summary: str
    estimated_tokens: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "code-review",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest):
    """
    Main code review endpoint
    - Receives only diff context (changed lines + 5-line context window)
    - Uses rule-based workflows for 70% of standard review patterns
    - Invokes LLM only for complex logic analysis
    """
    import uuid
    
    review_id = str(uuid.uuid4())
    findings = analyze_diffs(request.diffs)
    
    # Simple approval logic
    critical_findings = [f for f in findings if f.severity == "critical"]
    approval = len(critical_findings) == 0
    
    # Token estimation: only diffs loaded
    token_estimate = sum(len(d.changes.split()) * 2 for d in request.diffs)
    
    return ReviewResponse(
        review_id=review_id,
        status="approved" if approval else "revision_required",
        findings=findings,
        approval=approval,
        summary=f"Found {len(findings)} issue(s), {len(critical_findings)} critical",
        estimated_tokens=token_estimate
    )

def analyze_diffs(diffs: List[CodeDiff]) -> List[ReviewFinding]:
    # Placeholder static analysis
    return []

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
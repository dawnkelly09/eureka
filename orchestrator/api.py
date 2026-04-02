"""FastAPI endpoints for Eureka."""

import uuid
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator.config import MEMORY_DIR, logger
from orchestrator.memory import init_memory
from orchestrator.state import EurekaState
from orchestrator.graph import build_graph

app = FastAPI(title="Eureka", description="AI-first engineer onboarding factory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for run results
_runs: dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    repo_url: str


class AnalyzeResponse(BaseModel):
    run_id: str
    status: str


class ResultsResponse(BaseModel):
    run_id: str
    status: str
    repo_url: Optional[str] = None
    repo_name: Optional[str] = None
    architecture: Optional[str] = None
    claude_md: Optional[str] = None
    hooks: Optional[str] = None
    skills_file: Optional[str] = None
    error: Optional[str] = None


async def _run_pipeline(run_id: str, repo_url: str):
    """Run the full Eureka pipeline in the background."""
    try:
        graph = build_graph()
        initial_state: EurekaState = {
            "run_id": run_id,
            "repo_url": repo_url,
            "repo_name": "",
            "memory_file": f"memory/{run_id}.md",
            "repo_structure": None,
            "stack_detected": None,
            "architecture_overview": None,
            "claude_md": None,
            "hooks": None,
            "skills_file": None,
            "current_node": "start",
            "error": None,
        }

        result = await graph.ainvoke(initial_state)

        _runs[run_id] = {
            "status": "completed",
            "repo_url": repo_url,
            "repo_name": result.get("repo_name", ""),
            "architecture": result.get("architecture_overview"),
            "claude_md": result.get("claude_md"),
            "hooks": result.get("hooks"),
            "skills_file": result.get("skills_file"),
            "error": None,
        }
        logger.info(f"Pipeline completed for {run_id}")
    except Exception as e:
        logger.error(f"Pipeline failed for {run_id}: {e}")
        _runs[run_id] = {
            "status": "failed",
            "repo_url": repo_url,
            "error": str(e),
        }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Start analyzing a GitHub repo."""
    run_id = str(uuid.uuid4())[:8]
    init_memory(run_id, request.repo_url)
    _runs[run_id] = {"status": "running", "repo_url": request.repo_url}
    background_tasks.add_task(_run_pipeline, run_id, request.repo_url)
    return AnalyzeResponse(run_id=run_id, status="running")


@app.get("/results/{run_id}", response_model=ResultsResponse)
async def get_results(run_id: str):
    """Get the results of a pipeline run."""
    if run_id not in _runs:
        return ResultsResponse(run_id=run_id, status="not_found")
    run = _runs[run_id]
    return ResultsResponse(
        run_id=run_id,
        status=run.get("status", "unknown"),
        repo_url=run.get("repo_url"),
        repo_name=run.get("repo_name"),
        architecture=run.get("architecture"),
        claude_md=run.get("claude_md"),
        hooks=run.get("hooks"),
        skills_file=run.get("skills_file"),
        error=run.get("error"),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}

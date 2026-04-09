"""FastAPI endpoints for Eureka."""

import asyncio
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator.config import logger
from orchestrator.ghost_rag import destroy_ghost_rag
from orchestrator.memory import init_memory
from orchestrator.state import EurekaState
from orchestrator.graph import build_graph
from orchestrator.supabase_client import upsert_run

app = FastAPI(title="Eureka", description="AI-first engineer onboarding factory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run results — persisted to disk so --reload doesn't lose them
_RUNS_FILE = Path("memory/_runs.json")


def _load_runs() -> dict[str, dict]:
    if _RUNS_FILE.exists():
        try:
            return json.loads(_RUNS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


_runs_lock = asyncio.Lock()


async def _save_runs() -> None:
    async with _runs_lock:
        _RUNS_FILE.parent.mkdir(exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=_RUNS_FILE.parent, suffix=".tmp")
        os.close(fd)
        try:
            Path(tmp).write_text(json.dumps(_runs, indent=2))
            Path(tmp).replace(_RUNS_FILE)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise


_runs: dict[str, dict] = _load_runs()


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
    skills: Optional[str] = None
    error: Optional[str] = None


class RepoResponse(BaseModel):
    repo_url: str
    repo_name: str
    architecture: str
    claude_md: str
    hooks: str
    skills: str


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
            "skills": result.get("skills_file"),
            "error": None,
        }
        await _save_runs()
        upsert_run(run_id, _runs[run_id])
        logger.info(f"Pipeline completed for {run_id}")
    except Exception as e:
        logger.error(f"Pipeline failed for {run_id}: {e}")
        _runs[run_id] = {
            "status": "failed",
            "repo_url": repo_url,
            "error": str(e),
        }
        await _save_runs()
        upsert_run(run_id, _runs[run_id])
    finally:
        destroy_ghost_rag(run_id)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Start analyzing a GitHub repo."""
    run_id = str(uuid.uuid4())[:8]
    init_memory(run_id, request.repo_url)
    _runs[run_id] = {"status": "running", "repo_url": request.repo_url}
    await _save_runs()
    upsert_run(run_id, _runs[run_id])
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
        skills=run.get("skills"),
        error=run.get("error"),
    )


@app.get("/repos")
async def list_repos() -> dict[str, RepoResponse]:
    """Return all completed runs keyed by repo name (latest run wins)."""
    repos: dict[str, RepoResponse] = {}
    for run in _runs.values():
        if run.get("status") != "completed":
            continue
        name = run.get("repo_name", "")
        if not name:
            continue
        repos[name] = RepoResponse(
            repo_url=run.get("repo_url", ""),
            repo_name=name,
            architecture=run.get("architecture", ""),
            claude_md=run.get("claude_md", ""),
            hooks=run.get("hooks", ""),
            skills=run.get("skills", ""),
        )
    return repos


@app.get("/health")
async def health():
    return {"status": "ok"}

"""Architect node — generates architecture overview from explorer output."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log
from orchestrator.mcp_tools import create_ghost_rag_server


@traceable(run_type="chain", name="architect_node")
async def run_architect(state: EurekaState) -> EurekaState:
    """Generate an architecture overview document."""
    audit_log(state["run_id"], "architect_start", state["repo_name"])

    mcp_server = create_ghost_rag_server(state["run_id"])

    output = await run_agent(
        state,
        skill_file="architect/SKILL.md",
        memory_section="Architecture",
        mcp_server=mcp_server,
    )

    audit_log(state["run_id"], "architect_done", f"{len(output)} chars")
    return {**state, "architecture_overview": output, "current_node": "architect"}

"""Hooks generator node — produces stack-appropriate Claude Code hooks."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log
from orchestrator.mcp_tools import create_ghost_rag_server


@traceable(run_type="chain", name="hooks_node")
async def run_hooks(state: EurekaState) -> EurekaState:
    """Generate hook configurations for this repo's stack."""
    audit_log(state["run_id"], "hooks_start", state["repo_name"])

    mcp_server = create_ghost_rag_server(state["run_id"])

    output = await run_agent(
        state,
        skill_file="hooks-generator/SKILL.md",
        memory_section="Hooks",
        mcp_server=mcp_server,
    )

    audit_log(state["run_id"], "hooks_done", f"{len(output)} chars")
    return {**state, "hooks": output, "current_node": "hooks"}

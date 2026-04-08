"""CLAUDE.md writer node — generates an onboarding-focused CLAUDE.md."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log
from orchestrator.mcp_tools import create_ghost_rag_server


@traceable(run_type="chain", name="claude_md_node")
async def run_claude_md(state: EurekaState) -> EurekaState:
    """Generate a CLAUDE.md file tuned to this repo."""
    audit_log(state["run_id"], "claude_md_start", state["repo_name"])

    mcp_server = create_ghost_rag_server(state["run_id"])

    output = await run_agent(
        state,
        skill_file="claude-md-writer/SKILL.md",
        memory_section="CLAUDE.md",
        mcp_server=mcp_server,
    )

    audit_log(state["run_id"], "claude_md_done", f"{len(output)} chars")
    return {**state, "claude_md": output, "current_node": "claude_md"}

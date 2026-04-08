"""Skills writer node — produces a repo-specific SKILL.md."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log
from orchestrator.mcp_tools import create_ghost_rag_server


@traceable(run_type="chain", name="skills_node")
async def run_skills(state: EurekaState) -> EurekaState:
    """Generate a SKILL.md tuned to this repo's patterns."""
    audit_log(state["run_id"], "skills_start", state["repo_name"])

    mcp_server = create_ghost_rag_server(state["run_id"])

    output = await run_agent(
        state,
        skill_file="skills-writer/SKILL.md",
        memory_section="Skills",
        mcp_server=mcp_server,
    )

    audit_log(state["run_id"], "skills_done", f"{len(output)} chars")
    return {**state, "skills_file": output, "current_node": "skills"}

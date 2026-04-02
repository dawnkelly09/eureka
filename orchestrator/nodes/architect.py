"""Architect node — generates architecture overview from explorer output."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log


@traceable(run_type="chain", name="architect_node")
async def run_architect(state: EurekaState) -> EurekaState:
    """Generate an architecture overview document."""
    audit_log(state["run_id"], "architect_start", state["repo_name"])

    output = await run_agent(
        state,
        skill_file="architect/SKILL.md",
        memory_section="Architecture",
        extra_prompt=(
            f"The repo is: {state['repo_url']}\n"
            f"Write an architecture overview following your skill instructions. "
            f"The Explorer has already mapped the repo — read its output from the memory file above."
        ),
    )

    audit_log(state["run_id"], "architect_done", f"{len(output)} chars")
    return {**state, "architecture_overview": output, "current_node": "architect"}

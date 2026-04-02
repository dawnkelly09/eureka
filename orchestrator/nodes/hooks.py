"""Hooks generator node — produces stack-appropriate Claude Code hooks."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log


@traceable(run_type="chain", name="hooks_node")
async def run_hooks(state: EurekaState) -> EurekaState:
    """Generate hook configurations for this repo's stack."""
    audit_log(state["run_id"], "hooks_start", state["repo_name"])

    output = await run_agent(
        state,
        skill_file="hooks-generator/SKILL.md",
        memory_section="Hooks",
        extra_prompt=(
            f"The repo is: {state['repo_url']}\n"
            f"Generate stack-appropriate Claude Code hooks following your skill instructions. "
            f"The Explorer output in the memory file above has the detected stack."
        ),
    )

    audit_log(state["run_id"], "hooks_done", f"{len(output)} chars")
    return {**state, "hooks": output, "current_node": "hooks"}

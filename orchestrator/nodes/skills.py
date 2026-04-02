"""Skills writer node — produces a repo-specific SKILL.md."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log


@traceable(run_type="chain", name="skills_node")
async def run_skills(state: EurekaState) -> EurekaState:
    """Generate a SKILL.md tuned to this repo's patterns."""
    audit_log(state["run_id"], "skills_start", state["repo_name"])

    output = await run_agent(
        state,
        skill_file="skills-writer/SKILL.md",
        memory_section="Skills",
        extra_prompt=(
            f"The repo is: {state['repo_url']}\n"
            f"Write a repo-specific SKILL.md following your skill instructions. "
            f"All previous agent outputs are in the memory file above."
        ),
    )

    audit_log(state["run_id"], "skills_done", f"{len(output)} chars")
    return {**state, "skills_file": output, "current_node": "skills"}

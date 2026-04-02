"""CLAUDE.md writer node — generates an onboarding-focused CLAUDE.md."""

from langsmith import traceable

from orchestrator.agent_runner import run_agent
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log


@traceable(run_type="chain", name="claude_md_node")
async def run_claude_md(state: EurekaState) -> EurekaState:
    """Generate a CLAUDE.md file tuned to this repo."""
    audit_log(state["run_id"], "claude_md_start", state["repo_name"])

    output = await run_agent(
        state,
        skill_file="claude-md-writer/SKILL.md",
        memory_section="CLAUDE.md",
        extra_prompt=(
            f"The repo is: {state['repo_url']}\n"
            f"Write a CLAUDE.md following your skill instructions. "
            f"The Explorer and Architect outputs are in the memory file above. "
            f"This must be visibly better than what /init produces."
        ),
    )

    audit_log(state["run_id"], "claude_md_done", f"{len(output)} chars")
    return {**state, "claude_md": output, "current_node": "claude_md"}

"""Core agent runner — calls Claude API to generate onboarding artifacts."""

import anthropic
from langsmith import traceable

from orchestrator.config import SKILLS_DIR, MEMORY_DIR, logger
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log
from orchestrator.memory import append_memory


@traceable(run_type="chain", name="run_agent")
async def run_agent(
    state: EurekaState,
    skill_file: str,
    memory_section: str,
    extra_prompt: str = "",
) -> str:
    """Call Claude to generate an artifact based on skill instructions and memory context."""
    run_id = state["run_id"]
    memory_content = (MEMORY_DIR / f"{run_id}.md").read_text()
    skill_content = (SKILLS_DIR / skill_file).read_text()

    repo_url = state["repo_url"]
    repo_name = state.get("repo_name", "")

    system_prompt = (
        f"You are an expert software engineer analyzing the repo: {repo_url} ({repo_name}).\n\n"
        f"## Your Skill Instructions\n\n{skill_content}\n\n"
        f"Follow the skill instructions precisely. Produce ONLY the artifact described — "
        f"no preamble, no meta-commentary, no 'Here is the output:' wrapper. "
        f"Just the content itself."
    )

    user_prompt = f"## Memory File (context from previous agents)\n\n{memory_content}"
    if extra_prompt:
        user_prompt += f"\n\n{extra_prompt}"

    audit_log(run_id, f"agent_start:{memory_section}", skill_file)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    output = response.content[0].text
    append_memory(run_id, memory_section, output)
    audit_log(run_id, f"agent_done:{memory_section}", f"{len(output)} chars")
    return output

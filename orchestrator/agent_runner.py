"""Core agent runner — spawns Claude Code sessions to generate onboarding artifacts."""

from claude_agent_sdk import query as claude_query, ClaudeAgentOptions
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
    """
    Run a Claude Code agent session.
    Uses Claude Max plan via claude-agent-sdk, not API credits.

    Same interface as before — callers (node files) don't change.
    """
    run_id = state["run_id"]
    memory_content = (MEMORY_DIR / f"{run_id}.md").read_text()
    skill_content = (SKILLS_DIR / skill_file).read_text()

    repo_url = state["repo_url"]
    repo_name = state.get("repo_name", "")

    prompt = (
        f"You are an expert software engineer analyzing the repo: {repo_url} ({repo_name}).\n\n"
        f"## Your Skill Instructions\n\n{skill_content}\n\n"
        f"Follow the skill instructions precisely. Produce ONLY the artifact described — "
        f"no preamble, no meta-commentary, no 'Here is the output:' wrapper. "
        f"Just the content itself.\n\n"
        f"## Memory File (context from previous agents)\n\n{memory_content}"
    )
    if extra_prompt:
        prompt += f"\n\n{extra_prompt}"

    audit_log(run_id, f"agent_start:{memory_section}", skill_file)

    import os
    # Pass a clean env to the SDK without ANTHROPIC_API_KEY so it uses OAuth
    # (Max plan) auth. This avoids mutating os.environ globally — a real API
    # key in .env stays available to anything else that needs it.
    sdk_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Glob", "Grep"],
        env=sdk_env,
    )

    output_parts: list[str] = []
    async for message in claude_query(prompt=prompt, options=options):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    output_parts.append(block.text)

    output = "\n".join(output_parts)

    append_memory(run_id, memory_section, output)
    audit_log(run_id, f"agent_done:{memory_section}", f"{len(output)} chars")
    return output

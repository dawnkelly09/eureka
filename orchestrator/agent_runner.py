"""Core agent runner — spawns Claude Code sessions to generate onboarding artifacts."""

from claude_agent_sdk import query as claude_query, ClaudeAgentOptions
from claude_agent_sdk.types import McpSdkServerConfig
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
    mcp_server: McpSdkServerConfig | None = None,
) -> str:
    """
    Run a Claude Code agent session.
    Uses Claude Max plan via claude-agent-sdk, not API credits.

    Same interface as before — callers (node files) don't change.
    """
    run_id = state["run_id"]
    memory_content = (MEMORY_DIR / f"{run_id}.md").read_text()
    raw_skill = (SKILLS_DIR / skill_file).read_text()

    # Strip YAML frontmatter from skill file before injecting into prompt
    skill_content = raw_skill
    if raw_skill.startswith("---"):
        parts = raw_skill.split("---", 2)
        if len(parts) >= 3:
            skill_content = parts[2].strip()

    # Load output template from the skill's assets/ directory
    skill_dir = SKILLS_DIR / skill_file.rsplit("/", 1)[0] if "/" in skill_file else SKILLS_DIR / skill_file
    template_path = skill_dir / "assets" / "TEMPLATE.md"
    template_content = template_path.read_text() if template_path.exists() else ""

    repo_url = state["repo_url"]
    repo_name = state.get("repo_name", "")

    prompt = (
        f"You are an expert software engineer analyzing the repo: {repo_url} ({repo_name}).\n\n"
        f"## Your Skill Instructions\n\n{skill_content}\n\n"
    )

    if template_content:
        import re
        # Strip HTML comments — they're authoring hints, not agent instructions
        filled_template = re.sub(r"<!--.*?-->", "", template_content, flags=re.DOTALL).strip()
        filled_template = filled_template.replace("REPO_NAME", repo_name)
        prompt += (
            f"## Output Template\n\n"
            f"Use this exact structure for your output. "
            f"Keep every section heading and fill in real content under each one. "
            f"Output ONLY the filled-in document.\n\n"
            f"{filled_template}\n\n"
        )

    prompt += (
        f"## CRITICAL OUTPUT RULES\n\n"
        f"Your text output IS the artifact. Do your research and analysis using tools, "
        f"then output the completed document as plain text. "
        f"Do NOT put the artifact content in your thinking — it must be in your text output. "
        f"No preamble, no meta-commentary, no 'Here is the output:' wrapper. "
        f"Just the filled-in template content.\n\n"
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

    allowed = ["Read", "Glob", "Grep"]
    mcp_servers = {}

    if mcp_server:
        mcp_servers["ghost-rag"] = mcp_server
        allowed.extend(["search_repo", "get_file"])

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=allowed,
        mcp_servers=mcp_servers,
        env=sdk_env,
    )

    output_parts: list[str] = []
    async for message in claude_query(prompt=prompt, options=options):
        msg_type = getattr(message, "type", "unknown")
        logger.info(f"[{run_id}] SDK message type={msg_type}")
        if hasattr(message, "content"):
            for block in message.content:
                block_type = getattr(block, "type", "unknown")
                block_text = getattr(block, "text", "")
                preview = (block_text[:80] + "...") if len(block_text) > 80 else block_text
                logger.info(f"[{run_id}] block type={block_type} len={len(block_text)} preview={preview!r}")
                if block_type == "text" and block_text:
                    output_parts.append(block_text)
        if hasattr(message, "result"):
            result_text = getattr(message, "result", "")
            if result_text:
                preview = (result_text[:80] + "...") if len(result_text) > 80 else result_text
                logger.info(f"[{run_id}] result message len={len(result_text)} preview={preview!r}")
                output_parts.append(result_text)

    output = "\n".join(output_parts)

    # Strip preamble — anything before the first markdown heading
    import re
    heading_match = re.search(r"^(#{1,6}\s)", output, flags=re.MULTILINE)
    if heading_match:
        output = output[heading_match.start():]

    logger.info(f"[{run_id}] Final output: {len(output)} chars, {len(output_parts)} parts")

    append_memory(run_id, memory_section, output)
    audit_log(run_id, f"agent_done:{memory_section}", f"{len(output)} chars")
    return output

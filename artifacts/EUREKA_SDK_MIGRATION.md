# Eureka — Agent Migration: Anthropic API → Claude Code SDK

## What We Did and Why

Eureka's four agents (Architect, CLAUDE.md Writer, Hooks Generator, Skills Writer) previously
called `anthropic.messages.create()` via a centralized `agent_runner.py`. Every pipeline run
burned API credits from the `ANTHROPIC_API_KEY` balance.

The factory pattern Eureka is based on ([ashtilawat/minimum-viable-factory](https://github.com/ashtilawat/minimum-viable-factory))
uses the `claude-agent-sdk` Python library instead. Agents run as full Claude Code sessions —
they use the operator's Claude Max plan rather than API credits, they get tool access (Read, Glob,
Grep), and the architecture is consistent with what Eureka itself documents in its onboarding output.

**Goal:** Swap `agent_runner.py` from `anthropic.messages.create()` to `claude-agent-sdk`.
The four node files already delegate to `run_agent()` and needed no changes. The Explorer node
stays as-is — it's intentionally deterministic Python, not an agent.

---

## The Pattern (from minimum-viable-factory)

The source factory uses the `claude-agent-sdk` Python library — **not** `subprocess.run()` against
the CLI. This is an important distinction that we got wrong initially (see [What We Tried First](#what-we-tried-first-subprocess)).

```python
from claude_agent_sdk import query as claude_query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    allowed_tools=["Read", "Glob", "Grep"],
)

output_parts: list[str] = []
async for message in claude_query(prompt=prompt, options=options):
    if hasattr(message, "content"):
        for block in message.content:
            if hasattr(block, "text"):
                output_parts.append(block.text)

output = "\n".join(output_parts)
```

Key things to understand:

- `claude-agent-sdk` is a pip package (`pip install claude-agent-sdk`), requires **Python >= 3.10**
- It bundles its own Claude Code CLI internally — no separate `npm install` needed
- `claude_query()` is natively async — no `asyncio.to_thread()` wrapper needed
- Output is streamed as structured messages with `.content[].text` blocks
- `permission_mode="bypassPermissions"` lets the agent use tools without prompting
- `allowed_tools` whitelists which tools the agent can use
- Runs on the operator's Claude Max plan via OAuth, not `ANTHROPIC_API_KEY`

---

## What We Replaced

The actual code lived in `orchestrator/agent_runner.py` — the **only file** that imported
`anthropic`. The four node files already delegated to `run_agent()`.

Previous `agent_runner.py` (abbreviated):

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
)
output = response.content[0].text
```

The node files (e.g. `architect.py`) just call:

```python
output = await run_agent(
    state,
    skill_file="architect/SKILL.md",
    memory_section="Architecture",
    extra_prompt="...",
)
```

Because the interface stayed the same, **only `agent_runner.py` needed to change**.

---

## What We Tried First (Subprocess)

Our initial plan was to shell out to the `claude` CLI:

```python
result = subprocess.run(
    ["claude", "-p", prompt, "--output-format", "text", "--max-turns", "3"],
    capture_output=True, text=True, timeout=AGENT_TIMEOUT,
)
output = result.stdout.strip()
```

This approach had two problems:

1. **Empty stdout.** The CLI returned no output when invoked from a Python subprocess in the
   uvicorn server, even though it worked fine from a terminal. The exact cause wasn't fully
   diagnosed before we switched approaches.

2. **Environment variable poisoning.** `python-dotenv` loads `ANTHROPIC_API_KEY` from `.env`
   into the process environment. The subprocess inherits it. The CLI sees the key and tries to
   use it instead of OAuth — failing with `"Invalid API key"` if the key is a placeholder.
   The fix was stripping the key from the subprocess env, but this was a symptom of a deeper
   mismatch: the factory doesn't use subprocess at all.

After examining the actual minimum-viable-factory source, we found it uses `claude-agent-sdk`,
not CLI subprocess. We switched to that approach.

---

## The Final Implementation

### agent_runner.py (the only code change)

```python
"""Core agent runner — spawns Claude Code sessions to generate onboarding artifacts."""

import os

from claude_agent_sdk import query as claude_query, ClaudeAgentOptions
from langsmith import traceable

from orchestrator.config import SKILLS_DIR, MEMORY_DIR, logger
from orchestrator.state import EurekaState
from orchestrator.audit import audit_log
from orchestrator.memory import append_memory

# Strip ANTHROPIC_API_KEY from environment so the SDK uses OAuth (Max plan)
# auth instead of any API key loaded from .env by python-dotenv.
os.environ.pop("ANTHROPIC_API_KEY", None)


@traceable(run_type="chain", name="run_agent")
async def run_agent(
    state: EurekaState,
    skill_file: str,
    memory_section: str,
    extra_prompt: str = "",
) -> str:
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

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Glob", "Grep"],
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
```

Design decisions:

- **`os.environ.pop("ANTHROPIC_API_KEY", None)`** at module load — the SDK (which bundles its
  own CLI) still checks for this env var. If python-dotenv loads a placeholder, the SDK fails
  with an opaque auth error. Stripping it forces OAuth.

- **`allowed_tools=["Read", "Glob", "Grep"]`** — Eureka agents only need to read and search.
  They don't need Write, Edit, or Bash. Restricting tools prevents agents from accidentally
  modifying files.

- **Natively async** — `claude_query()` is an async generator, so it works directly in
  LangGraph's async nodes. No `asyncio.to_thread()` needed (unlike the subprocess approach).

- **`@traceable` preserved** for LangSmith tracing continuity.

- **Prompt merges system + user into one string** — the SDK takes a single `prompt`, not
  separate system/user messages like the Messages API.

---

## All Changes Made

| File                           | Change                                                      |
| ------------------------------ | ----------------------------------------------------------- |
| `orchestrator/agent_runner.py` | Rewrite: `anthropic` → `claude-agent-sdk`                   |
| `requirements.txt`             | Remove `anthropic`, add `claude-agent-sdk`                  |
| `orchestrator/config.py`       | Update `ANTHROPIC_API_KEY` comment                          |
| `.env.example`                 | Add comments explaining what's optional now                  |
| `README.md`                    | Update setup instructions and tech stack                    |
| `.claude/CLAUDE.md`            | Updated architecture description                            |

**Not changed** (and why):

| File                              | Why No Change                                                  |
| --------------------------------- | -------------------------------------------------------------- |
| `orchestrator/nodes/architect.py` | Already delegates to `run_agent()` — interface unchanged       |
| `orchestrator/nodes/claude_md.py` | Already delegates to `run_agent()` — interface unchanged       |
| `orchestrator/nodes/hooks.py`     | Already delegates to `run_agent()` — interface unchanged       |
| `orchestrator/nodes/skills.py`    | Already delegates to `run_agent()` — interface unchanged       |

---

## Gotcha: ANTHROPIC_API_KEY Environment Variable Poisoning

This hit us twice — once with subprocess, once with the SDK. Both the CLI and the SDK check for
`ANTHROPIC_API_KEY` in the environment. If python-dotenv loads a placeholder value (e.g.,
`sk-ant-` from `.env`), the SDK tries to use it as an API key instead of OAuth, and fails.

**Symptoms:**
- With subprocess: agents return `"Invalid API key · Fix external API key"` (38 chars) in ~2s
- With SDK: `Command failed with exit code 1` error

**Fix:** Strip the key from the environment before the SDK loads:
```python
os.environ.pop("ANTHROPIC_API_KEY", None)
```

This is at module level in `agent_runner.py` so it runs once at import time.

**Prevention for new projects:** Don't put placeholder API keys in `.env` files. Either use a
real key or leave the variable unset. The `.env.example` now has comments explaining this.

---

## Prerequisites

- **Python >= 3.10** — `claude-agent-sdk` requires it. We upgraded from 3.9.6 to 3.12.
- **Claude Max plan** — the SDK uses OAuth auth tied to the operator's Max subscription.
  Run `claude login` once to authenticate.
- No separate `npm install` needed — the SDK bundles its own CLI.

---

## Validation

```bash
# Verify Python version (must be >= 3.10)
python3 --version

# Install dependencies
pip install -r requirements.txt

# Verify claude auth (should not prompt for API key)
python3 -c "
import asyncio, os
os.environ.pop('ANTHROPIC_API_KEY', None)
from claude_agent_sdk import query as claude_query, ClaudeAgentOptions
async def test():
    async for msg in claude_query(prompt='Say hello.', options=ClaudeAgentOptions()):
        if hasattr(msg, 'content'):
            for b in msg.content:
                if hasattr(b, 'text'): print(b.text)
asyncio.run(test())
"

# Run the full pipeline
uvicorn orchestrator:app --reload
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/fastapi/fastapi"}'
```

Check that:

- Pipeline completes without API key errors
- Memory file has all four agent sections populated
- Output quality is comparable to previous API runs
- No `ANTHROPIC_API_KEY` charges in the Anthropic console
- LangSmith traces still appear (if configured)

---

## Applying to Other Repos

This migration applies to any project forked from minimum-viable-factory that still uses
`anthropic.messages.create()`. The steps are:

1. Upgrade Python to >= 3.10
2. Replace `anthropic` with `claude-agent-sdk` in requirements.txt
3. Rewrite the agent runner to use `claude_query()` (see implementation above)
4. Add `os.environ.pop("ANTHROPIC_API_KEY", None)` before SDK import
5. Verify the `run_agent()` interface didn't change so callers are unaffected
6. Update `.env.example`, README, and project docs

---

## Note on Aura

Aura is being built on top of Eureka. This migration was done in Eureka first. Apply the same
pattern to Aura's agents — don't let it inherit the API pattern.

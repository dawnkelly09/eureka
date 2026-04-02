# Day One — Claude Code Instructions

## Context

You are helping build **Eureka** — an AI-first engineer onboarding factory. It takes a GitHub repo URL as input and produces a complete onboarding package: architecture overview, CLAUDE.md, suggested hooks, and a starter Skills file.

This is being built to demonstrate AI-first engineering capability to Gauntlet AI for program acceptance. The deliverable is a deployed UI showing polished output for two target repos (FastAPI and Vite), plus the pipeline code on GitHub.

Read `EUREKA_SPEC.md` and `EUREKA_BUILD_PLAN.md` before doing anything else. They are your source of truth.

The starting point is the `minimum-viable-factory` repo structure. We are extending it, not rebuilding it.

## Today's Goal

By end of day one, we need:
1. The new repo scaffolded with the correct structure
2. The five Skill files written (this is the most important work today)
3. The Explorer agent working — able to ingest a real repo and write a useful memory file
4. Confidence that the pipeline can run end-to-end, even if outputs are rough

## Do This First

Before writing any new code, do the following in order:

### Step 1: Create the Eureka repo
Create a new directory called `eureka`. Initialize a git repo. This is NOT a fork of minimum-viable-factory — it's a new repo that borrows its patterns.

### Step 2: Copy the infrastructure you're keeping
From minimum-viable-factory, copy these files as-is (they need minimal changes):
- `orchestrator/agent_runner.py`
- `orchestrator/memory.py`
- `orchestrator/audit.py`
- `orchestrator/config.py` (update constants)
- `memory/_template.md` (update for Eureka's output shape)
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`

### Step 3: Write the Skill files

This is the most important work today. The Skill files are what make Eureka's output good. Write all five before touching the pipeline code.

**`explorer/SKILL.md`** — teaches the agent how to map a repo:
- Start with README, then dependency files, then directory structure
- Identify: primary language(s), framework, package manager, test setup, entry points
- Smart file sampling: pick files that reveal architecture, not files that are boilerplate
- Hard limits: max 50 files, max 200 lines per file
- Output format: structured summary the next agents can rely on

**`architect/SKILL.md`** — teaches the agent how to write an architecture overview:
- Audience: a new engineer on day one, not the author of the code
- Focus on: how pieces connect, key abstractions, what to understand first
- Include: a "mental model" section — the one thing you need to understand to make sense of everything else
- Do NOT: list every file, describe every function, produce a file tree
- Length: 400-600 words, readable in 5 minutes

**`claude-md-writer/SKILL.md`** — teaches the agent how to write a CLAUDE.md:
- Must be visibly better than what `/init` produces
- Required sections: Build & Dev Commands, Architecture (brief), Start Here (new section — where to begin), Gotchas (non-obvious things that bite new engineers), AI Working Patterns (how to work effectively with agents in this repo), Conventions
- "Start Here" and "AI Working Patterns" are Eureka's signature — they don't exist in /init output
- Be specific and opinionated. Generic advice is worse than no advice.

**`hooks-generator/SKILL.md`** — teaches the agent how to generate hooks:
- Detect the stack from the explorer output
- Python repos: suggest ruff (linting), mypy or pyright (type checking), pytest (tests)
- TypeScript repos: suggest ESLint, tsc --noEmit (type checking), vitest or jest
- All repos: DRY check hook (flag repeated code blocks), test runner hook
- Output format: ready-to-paste hook configurations with setup instructions
- Include the Claude Code settings.json snippet for each hook

**`skills-writer/SKILL.md`** — teaches the agent how to write a repo-specific Skills file:
- A Skills file teaches an AI agent how to work in a specific codebase
- Must be specific to this repo, not generic AI advice
- Include: navigation patterns (where to look for what), key conventions, common tasks and how to approach them, what good output looks like for this repo
- Length: 300-500 words
- The test: if you removed the repo name, could this Skills file apply to any repo? If yes, it's not specific enough.

### Step 4: Set up the LangGraph state schema
Create `orchestrator/state.py` with the Eureka state shape:

```python
from typing import TypedDict, Optional

class EurekaState(TypedDict):
    run_id: str
    repo_url: str
    repo_name: str
    memory_file: str
    # Explorer output
    repo_structure: Optional[str]
    stack_detected: Optional[dict]
    # Agent outputs
    architecture_overview: Optional[str]
    claude_md: Optional[str]
    hooks: Optional[str]
    skills_file: Optional[str]
    # Status
    current_node: str
    error: Optional[str]
```

### Step 5: Build the Explorer node
`orchestrator/nodes/explorer.py` — this is the highest-risk piece. Build it and test it on a real repo before anything else.

The explorer should:
1. Accept a GitHub URL
2. Shallow clone the repo (`git clone --depth=1`)
3. Read files in priority order (README → package files → directory listing → entry points → key source samples)
4. Respect hard limits (50 files max, 200 lines per file)
5. Write a structured summary to the memory file
6. Return the state with `repo_structure` and `stack_detected` populated

**Test it immediately on FastAPI:**
```bash
python -m orchestrator.nodes.explorer https://github.com/fastapi/fastapi
```

Read the memory file output. Is it useful? Does it capture what matters? Fix it before moving on.

### Step 6: Wire the pipeline graph
`orchestrator/graph.py` — sequential LangGraph graph:
```
explorer → architect → claude_md_writer → hooks_generator → skills_writer → done
```

No conditional edges, no interrupts for MVP.

### Step 7: FastAPI endpoint
`orchestrator/api.py` — single endpoint:
```
POST /analyze
  body: { repo_url: string }
  response: { run_id: string, status: string }

GET /results/{run_id}
  response: { architecture, claude_md, hooks, skills_file }
```

## What NOT to Do Today

- Do not build the Vite UI today (that's day two)
- Do not optimize for arbitrary repos (optimize for FastAPI and Vite)
- Do not add Linear, Slack, or any integrations beyond GitHub
- Do not spend time on error handling edge cases (happy path first)
- Do not try to make the output perfect on the first run — get it running, then improve

## End of Day Check

You're done for day one when:
- [ ] Repo scaffolded with correct structure
- [ ] All five Skill files written and specific (not generic)
- [ ] Explorer node runs successfully on `https://github.com/fastapi/fastapi`
- [ ] Memory file output from Explorer looks useful and structured
- [ ] LangGraph pipeline wired (even if only Explorer is working end-to-end)
- [ ] README started (just the concept and setup for now)

If the Explorer is working and the Skills files are written, day one is a success. Everything else builds on those two foundations.

## Repo to Create

Name: `eureka`
GitHub: push to `dawnkelly09/eureka` (public)
Description: "AI-first engineer onboarding factory. Repo in, onboarding package out."

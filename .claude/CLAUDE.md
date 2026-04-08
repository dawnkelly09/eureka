# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Is Eureka

AI-first engineer onboarding factory. Takes a GitHub repo URL, runs a 5-agent pipeline, and produces four artifacts: architecture overview, CLAUDE.md, suggested hooks, and a starter Skills file.

## Build & Dev Commands

- **Install**: `pip install -r requirements.txt` (Python >= 3.10)
- **Auth**: `claude login` (one-time, authenticates with Claude Max plan)
- **Configure**: `cp .env.example .env` and set `GITHUB_TOKEN`
- **Run API**: `uvicorn orchestrator:app --reload` (serves on :8000)
- **Run UI**: `cd ui && npm install && npm run dev` (Vite dev server proxies API calls to :8000)
- **Test Explorer standalone**: `python -m orchestrator.nodes.explorer https://github.com/fastapi/fastapi`
- **API smoke test**: `curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{"repo_url": "https://github.com/fastapi/fastapi"}'` then poll `GET /results/{run_id}`

There are no automated tests or linters configured.

## Architecture

### Pipeline

LangGraph orchestrates a sequential pipeline defined in `orchestrator/graph.py`:

```
Explorer → Architect → CLAUDE.md Writer → Hooks Generator → Skills Writer → Cleanup
```

**Explorer** (`orchestrator/nodes/explorer.py`) is the only node that runs locally as deterministic Python. It uses `gitingest` to clone and parse repos, then populates **Ghost RAG** — an ephemeral in-memory ChromaDB collection (`orchestrator/ghost_rag.py`). The cleanup node destroys this collection after the pipeline finishes.

The other four nodes are **Claude Code agent sessions** spawned via `claude-agent-sdk` through `orchestrator/agent_runner.py`. Each agent gets: its Skill file instructions, an output template from `assets/TEMPLATE.md`, and the shared memory file content. Agents use the Ghost RAG MCP server (`orchestrator/mcp_tools.py`) to query repo contents via `search_repo` (semantic) and `get_file` (path lookup) tools.

### Shared Memory

Agents communicate through a shared markdown file at `memory/{run_id}.md`. The file is append-only — each agent reads all previous sections and appends its own via `orchestrator/memory.py`. The template lives at `memory/_template.md`.

### State

`orchestrator/state.py` defines `EurekaState` (TypedDict) which flows through the LangGraph pipeline. Each node returns a new state dict with its outputs merged.

### API

`orchestrator/api.py` — FastAPI app. Runs pipeline in background tasks. Results stored in an in-memory dict (`_runs`), not persisted across restarts. Endpoints: `POST /analyze`, `GET /results/{run_id}`, `GET /repos` (completed runs), `GET /health`.

### UI

Vite + React + TypeScript in `ui/`. Fetches from `GET /repos`, renders artifacts in tabs with markdown viewer. The Vite dev server proxies `/repos`, `/analyze`, `/results`, `/health` to the API on :8000 (see `ui/vite.config.ts`).

## Key Conventions

- **Memory is append-only.** Never overwrite previous agent sections in `memory/{run_id}.md`.
- **Skill files drive output quality.** Each agent's behavior is defined by `.claude/skills/{agent}/SKILL.md` plus its `assets/TEMPLATE.md`. To improve output, improve the skill or template.
- **No ANTHROPIC_API_KEY needed.** Agents use `claude-agent-sdk` with OAuth (Claude Max plan). `agent_runner.py` strips `ANTHROPIC_API_KEY` from the env passed to the SDK to prevent auth poisoning from `.env` placeholders.
- **Ghost RAG is ephemeral.** Per-run ChromaDB collection, in-memory only, destroyed at pipeline end. Test files are excluded from the vector store (but remain in the directory tree).
- **Explorer filters aggressively.** See `EXCLUDE_PATTERNS` in `explorer.py`. Test files are kept in the tree but excluded from ChromaDB indexing.
- **Target repos for demo**: FastAPI and Vite. Optimize for these first.
- **CSS Modules for UI styling.** No Tailwind — use `.module.css` files.
- **Audit logs** go to `audit/{YYYY-MM-DD}.log` — append-only daily files.
- **LangSmith tracing** is optional. Most functions are decorated with `@traceable`.

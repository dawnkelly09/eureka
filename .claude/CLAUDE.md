# Eureka — Agent Context

You are working on Eureka, an AI-first engineer onboarding factory. It takes a GitHub repo URL and produces four artifacts: architecture overview, CLAUDE.md, suggested hooks, and a starter Skills file.

## Build & Dev Commands

- Install: `pip install -r requirements.txt`
- Run API: `uvicorn orchestrator:app --reload`
- Test Explorer: `python -m orchestrator.nodes.explorer https://github.com/fastapi/fastapi`
- Docker: `docker-compose up --build`

## Architecture

LangGraph orchestrates a sequential pipeline of 5 agents. Each agent has a Skill file in `.claude/skills/` that defines its behavior. Agents communicate through a shared memory file (`memory/{run_id}.md`) — each agent reads previous outputs and appends its own.

The Explorer node is different from the other four: it runs locally (no Claude Code SDK) to clone and analyze repos. The other four nodes spawn Claude Code sessions via `agent_runner.py`.

## Key Files

- `orchestrator/graph.py` — pipeline DAG definition
- `orchestrator/nodes/explorer.py` — repo ingestion (highest-risk component)
- `orchestrator/agent_runner.py` — Claude Code session spawner
- `orchestrator/api.py` — FastAPI endpoints
- `.claude/skills/*/SKILL.md` — agent skill files (the quality of output depends on these)

## Conventions

- Memory files are append-only. Never overwrite previous agent sections.
- Skill files are the source of truth for agent behavior. Improve output by improving skills.
- Target repos for demo: FastAPI and Vite. Optimize for these first.
- Explorer hard limits: 50 files max, 200 lines per file.

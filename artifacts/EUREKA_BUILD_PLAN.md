# Eureka — Technical Build Plan

## Starting Point

Fork from `dawnkelly09/minimum-viable-factory`. We are extending, not rebuilding. The following primitives carry over unchanged:

- Agent runner (`orchestrator/agent_runner.py`) — keeps Claude Code SDK pattern
- Memory system (`memory/`) — one markdown file per run, append-only
- Audit logging (`audit/`) — append-only event log
- Docker + docker-compose — execution environment
- LangGraph — pipeline orchestration (kept for graph pattern + LangSmith tracing, no human gates in MVP)

## What Changes

### Input

Factory input: Linear ticket webhook
Eureka input: GitHub repo URL (submitted via web UI or API endpoint)

### Agents / Skills

Factory skills: spec-writing, architecture, coding, code-review, test-writing, deploy-checklist
Eureka skills: explorer, architect, claude-md-writer, hooks-generator, skills-writer

### Output

Factory output: deployed web app (GitHub repo + Vercel deployment)
Eureka output: onboarding package (4 artifacts rendered in Vite UI + CSS modules for styling - No Tailwind!)

### Integrations

Factory MCPs: Linear, GitHub, Vercel, Supabase, Slack
Eureka MCPs: GitHub (read-only repo access) — everything else is dropped for MVP

## Repo Structure

```
eureka/
├── .claude/
│   ├── CLAUDE.md                    # Master context for all agent sessions
│   ├── settings.json                # MCP config (GitHub only)
│   └── skills/
│       ├── explorer/SKILL.md        # How to map and understand a repo
│       ├── architect/SKILL.md       # How to write an architecture overview
│       ├── claude-md-writer/SKILL.md # How to write a great CLAUDE.md
│       ├── hooks-generator/SKILL.md  # How to generate appropriate hooks
│       └── skills-writer/SKILL.md   # How to write a repo-specific Skills file
├── orchestrator/
│   ├── __init__.py
│   ├── config.py                    # Env vars, constants
│   ├── state.py                     # LangGraph state schema
│   ├── memory.py                    # Memory file init and append
│   ├── audit.py                     # Audit logging
│   ├── agent_runner.py              # Claude Code agent runner (from factory)
│   ├── graph.py                     # LangGraph DAG
│   ├── pipeline.py                  # Pipeline start + repo ingestion
│   ├── api.py                       # FastAPI endpoints
│   └── nodes/
│       ├── __init__.py
│       ├── explorer.py              # Repo ingestion + structure mapping
│       ├── architect.py             # Architecture overview generation
│       ├── claude_md.py             # CLAUDE.md generation
│       ├── hooks.py                 # Hooks generation
│       └── skills.py                # Skills file generation
├── memory/
│   └── _template.md
├── audit/
├── ui/                              # Vite + React + TypeScript frontend
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── RepoInput.tsx        # URL input + submit
│   │   │   ├── PackageViewer.tsx    # Renders the four outputs
│   │   │   ├── ArchitectureTab.tsx
│   │   │   ├── ClaudeMdTab.tsx
│   │   │   ├── HooksTab.tsx
│   │   │   └── SkillsTab.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## The Agent Pipeline

```
GitHub URL submitted
        |
Explorer Agent
  - Clones/fetches repo (shallow clone)
  - Maps directory structure
  - Identifies: language(s), framework(s), package manager, test setup
  - Reads: README, package.json/pyproject.toml, top-level files
  - Samples: key source files (not everything — smart selection)
  - Writes to memory file
        |
Architect Agent
  - Reads explorer output from memory
  - Writes architecture overview document
  - Focus: how pieces connect, key abstractions, where to start
  - Appends to memory file
        |
CLAUDE.md Writer Agent
  - Reads explorer + architect output from memory
  - Writes CLAUDE.md tuned to this specific repo
  - Must be visibly better than /init output
  - Includes: start-here orientation, gotchas, AI-working patterns
  - Appends to memory file
        |
Hooks Generator Agent
  - Reads explorer output (stack detection) from memory
  - Generates appropriate pre/post tool hooks
  - Copy-paste ready with setup instructions
  - Appends to memory file
        |
Skills Writer Agent
  - Reads all previous output from memory
  - Writes SKILL.md tuned to this repo's patterns
  - Specific to the domain, not generic
  - Appends to memory file
        |
Package assembled → API returns JSON → UI renders
```

## Repo Ingestion Strategy (Critical)

This is the highest-risk part. Do not try to ingest entire repos — context window overflow will kill the pipeline.

**File prioritization order:**

1. README.md (always)
2. package.json / pyproject.toml / requirements.txt (dependency map)
3. Top-level directory listing (structure map)
4. Key config files (vite.config.ts, setup.py, etc.)
5. Entry points (main.py, index.ts, src/index.ts, etc.)
6. Sample 3-5 source files from key directories (not all of them)

**Hard limits:**

- Max 50 files read per run
- Max 200 lines per file (truncate with note)
- Shallow clone (depth=1) — no history needed

## The UI

Vite + React + TypeScript. Single page application.

**Layout:**

- Header: Eureka wordmark + repo URL being viewed
- Left panel or tabs: Architecture | CLAUDE.md | Hooks | Skills
- Each tab renders the artifact with syntax highlighting where appropriate
- Copy button on each artifact
- "View on GitHub" link back to source repo

**For the demo:**
The deployed UI will have the FastAPI and Vite outputs pre-loaded as selectable examples. A user can also submit a new URL to run the pipeline. This means the demo works even if the live pipeline is slow — the evaluator can immediately see polished output for the target repos.

## Environment Variables

```
GITHUB_TOKEN=ghp_...              # For repo access (public repos work without this)
LANGCHAIN_API_KEY=lsv2_...        # Optional — LangSmith tracing
LANGCHAIN_PROJECT=eureka
LANGCHAIN_TRACING_V2=true
# Note: ANTHROPIC_API_KEY is not needed — agents use claude-agent-sdk with OAuth
```

## What We Are NOT Building in MVP

- Human approval gates (no LangGraph interrupt)
- Linear integration
- Slack notifications
- Vercel/Supabase deployment of the analyzed repo
- Support for private repos (public only for MVP)
- Arbitrary repo support (optimized for FastAPI and Vite, tested on others)

## Demo Deployment

- Pipeline: runs locally or on a simple VPS / Railway
- UI: deployed to Vercel (same pattern as personal site)
- Pre-loaded outputs for FastAPI and Vite baked into the UI as static JSON
- Live pipeline endpoint available but not required for the demo

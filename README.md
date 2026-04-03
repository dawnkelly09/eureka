# Eureka

AI-first engineer onboarding factory. Repo in, onboarding package out.

## What It Does

Point Eureka at any GitHub repo and get back a complete onboarding package:

1. **Architecture Overview** — how the codebase works, not just what files exist
2. **CLAUDE.md** — AI-tuned onboarding guide with "Start Here" and "AI Working Patterns" sections
3. **Suggested Hooks** — stack-appropriate Claude Code hooks, ready to paste
4. **Starter Skills File** — teaches AI agents how to work in this specific codebase

## How It Works

A multi-agent pipeline orchestrated with LangGraph:

```
GitHub URL → Explorer → Architect → CLAUDE.md Writer → Hooks Generator → Skills Writer → Package
```

Each agent has a specialized **Skill file** (in `.claude/skills/`) that defines its behavior and output quality. Agents communicate through a shared memory file (`memory/{run_id}.md`) — each agent reads previous outputs and appends its own.

The **Explorer** runs locally as a Python process to clone and analyze repos (50 files max, 200 lines per file). The other four agents call the Anthropic API with context from their Skill files and the shared memory.

## Setup

```bash
# Clone
git clone https://github.com/dawnkelly09/eureka.git
cd eureka

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys:
#   ANTHROPIC_API_KEY  — required, powers the four AI agents
#   GITHUB_TOKEN       — required, for cloning repos via the Explorer
#   LANGCHAIN_API_KEY  — optional, enables LangSmith tracing

# Run the API
uvicorn orchestrator:app --reload

# Run the UI (separate terminal)
cd ui && npm install && npm run dev
```

### Test the Explorer directly

```bash
python -m orchestrator.nodes.explorer https://github.com/fastapi/fastapi
```

## API

```bash
# Health check
curl http://localhost:8000/health

# Start analysis
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/fastapi/fastapi"}'

# Check results
curl http://localhost:8000/results/{run_id}
```

## Agent Skills

The quality of Eureka's output is driven by Skill files — structured prompts that teach each agent how to produce repo-specific artifacts:

| Agent | Skill File | What It Produces |
|-------|-----------|-----------------|
| Explorer | `.claude/skills/explorer/SKILL.md` | Repo structure, stack detection, file summaries |
| Architect | `.claude/skills/architect/SKILL.md` | Architecture overview with data flow and patterns |
| CLAUDE.md Writer | `.claude/skills/claude-md-writer/SKILL.md` | Onboarding-focused CLAUDE.md |
| Hooks Generator | `.claude/skills/hooks-generator/SKILL.md` | Stack-appropriate Claude Code hooks |
| Skills Writer | `.claude/skills/skills-writer/SKILL.md` | Starter Skills file for the target repo |

## Tech Stack

- **Pipeline**: Python, LangGraph, Anthropic API
- **API**: FastAPI
- **Frontend**: Vite + React + TypeScript
- **Tracing**: LangSmith (optional)

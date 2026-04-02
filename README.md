# Eureka

AI-first engineer onboarding factory. Repo in, onboarding package out.

## What It Does

Point Eureka at any GitHub repo and get back a complete onboarding package:

1. **Architecture Overview** — how the codebase works, not just what files exist
2. **CLAUDE.md** — AI-tuned onboarding guide with "Start Here" and "AI Working Patterns" sections
3. **Suggested Hooks** — stack-appropriate Claude Code hooks, ready to paste
4. **Starter Skills File** — teaches AI agents how to work in this specific codebase

## How It Works

A multi-agent pipeline powered by Claude Code and orchestrated with LangGraph:

```
GitHub URL → Explorer → Architect → CLAUDE.md Writer → Hooks Generator → Skills Writer → Package
```

Each agent has a specialized Skill file that teaches it how to produce high-quality, repo-specific output.

## Setup

```bash
# Clone
git clone https://github.com/dawnkelly09/eureka.git
cd eureka

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Run the API
uvicorn orchestrator:app --reload

# Or test the Explorer directly
python -m orchestrator.nodes.explorer https://github.com/fastapi/fastapi
```

## API

```bash
# Start analysis
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/fastapi/fastapi"}'

# Check results
curl http://localhost:8000/results/{run_id}
```

## Tech Stack

- **Pipeline**: Python, LangGraph, Anthropic API
- **API**: FastAPI
- **Frontend**: Vite + React + TypeScript
- **Tracing**: LangSmith (optional)

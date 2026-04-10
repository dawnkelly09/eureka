🚨 This repo will be archived publicly as a snapshot of how easy it is to have your pipeline run into the ground if you don't have a rigorous framework around validation that goes beyond testing. The pattern here is an token burning furnance. Observe and then walk away slowly. 🚨

I cloned Eureka from this point and started building on top here: [https://github.com/dawnkelly09/BYTEBEAST-ARENA]

## Eureka

POC implementation of an AI-first engineer onboarding factory. Repo in, onboarding package out.

## Why I Built This

This project is a living archive of my evolution as an AI Engineer. 

I wanted to get beyond "prompt and pray" and learn how to get consistent, quality, trustworthy outputs from LLMs and wasn't sure how to do it. Gauntlet AI's Ashalesh Tilawat (@ashtilawat) created [minimum-viable-factory](https://github.com/ashtilawat/minimum-viable-factory) for a Night School session. Attendees were invited to take the factory and extend, modify, and make it their own. Eureka is my work in progress toward developing an agentic development pipeline scaffold. 

I accidentally created a sort of three codebase flywheel: 

- minimum-viable-factory: my fork is a static state representation of my starting point in this journey
- Eureka: proof of concept layer somewhere in between "it works on my machine" and deployed, monetized application
- Aura (private): implementation layer where the concepts validated in Eureka are applied to Aura and calibrated to the target audience. This is the layer that will eventually be exposed for user testing 

The factory hit me right at the sweet spot for my current engineering level: it showed me the entire concept of an end to end pipeline in one zoomed out view. Before this, I didn't have a picture of how an agent pipeline was shaped that included observability. I had a minimal framework for evaluation but it was crude: manual runs which I timed followed by a user interview with the agent to surface friction points. Just seeing how a pipeline takes shape was an unlock for me.

I went to work on how to make my own version of this and Eureka is the result. I was pretty proud of it. Then I went to another Night School session and Ash broke my brain with his "How to interview like an AI-first engineer" lecture. It was recorded and supposed to surface on Gauntlet's socials at some point. If you are interested in AI Engineering, it's worth your time. At a minimum, drop it to a summarizer and get the take aways. It's the best rubric I've seen, I'm speedrunning it, and this repo is the documentation. 

## What It Does

Point Eureka at any GitHub repo and get back a complete onboarding package:

1. **Architecture Overview** — how the codebase works, not just what files exist
2. **CLAUDE.md** — AI-tuned onboarding guide with "Start Here" and "AI Working Patterns" sections
3. **Suggested Hooks** — stack-appropriate Claude Code hooks, ready to paste
4. **Starter Skills File** — teaches AI agents how to work in this specific codebase

Currently, these artifacts are presented documentation style. The implementation layer will integrate these outputs with UI elements to create the Aura user experience. 

## How It Works

A multi-agent pipeline orchestrated with LangGraph:

```
GitHub URL → Explorer → Architect → CLAUDE.md Writer → Hooks Generator → Skills Writer → Package
```

Each agent has a specialized **Skill file** (in `.claude/skills/`) that defines its behavior and output quality. Agents communicate through a shared memory file (`memory/{run_id}.md`) — each agent reads previous outputs and appends its own.

The **Explorer** runs locally as a Python process to clone and analyze repos (50 files max, 200 lines per file). The other four agents run as Claude Code sessions via the `claude-agent-sdk` Python library, using your Claude Max plan — no API credits needed.

## Setup

```bash
# Clone
git clone https://github.com/dawnkelly09/eureka.git
cd eureka

# Install dependencies (requires Python >= 3.10)
pip install -r requirements.txt
claude login  # authenticate with your Claude Max plan (one-time setup)

# Configure
cp .env.example .env
# Edit .env with your keys:
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

| Agent            | Skill File                                 | What It Produces                                  |
| ---------------- | ------------------------------------------ | ------------------------------------------------- |
| Explorer         | `.claude/skills/explorer/SKILL.md`         | Repo structure, stack detection, file summaries   |
| Architect        | `.claude/skills/architect/SKILL.md`        | Architecture overview with data flow and patterns |
| CLAUDE.md Writer | `.claude/skills/claude-md-writer/SKILL.md` | Onboarding-focused CLAUDE.md                      |
| Hooks Generator  | `.claude/skills/hooks-generator/SKILL.md`  | Stack-appropriate Claude Code hooks               |
| Skills Writer    | `.claude/skills/skills-writer/SKILL.md`    | Starter Skills file for the target repo           |

## Tech Stack

- **Pipeline**: Python, LangGraph, Claude Code SDK
- **API**: FastAPI
- **Frontend**: Vite + React + TypeScript
- **Tracing**: LangSmith (optional)

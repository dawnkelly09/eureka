# Eureka — Product Spec

## What It Is

Eureka is an AI-first engineer onboarding factory. Point it at any GitHub repo and get back a complete onboarding package that tells a new engineer not just what the codebase is, but how to work in it — as an AI-first developer.

**The one-line pitch:** Claude Code's `/init` tells you what the repo is. Eureka tells you how to work in it.

## The Problem It Solves

When a new engineer joins a team, they face two gaps:

1. **Codebase comprehension** — what is this thing, how does it work, where do I start?
2. **AI-first setup** — how do I configure my AI tools to actually work effectively in this specific repo?

Neither gap is solved well today. `/init` produces a reference document. It doesn't produce an onboarding experience. It doesn't generate a Skills file tuned to the repo's patterns. It doesn't suggest hooks appropriate to the actual stack. It doesn't tell you the non-obvious things that will bite you.

Eureka fills both gaps in a single pipeline run.

## Target Demo Repos

- **FastAPI** (`https://github.com/fastapi/fastapi`) — Python backend, well-known, real complexity
- **Vite** (`https://github.com/vitejs/vite`) — TypeScript frontend, widely recognized, non-trivial monorepo structure

These repos were chosen because any evaluator will immediately know whether the output is accurate. They are the ground truth for the demo.

## The Four Outputs

### 1. Architecture Overview
A human-readable document explaining how the codebase works — not just what files exist, but how the pieces connect, what the key abstractions are, and what a new engineer needs to understand first. Opinionated and specific, not a file tree dump.

### 2. CLAUDE.md
A generated CLAUDE.md tuned specifically to this repo. Goes beyond what `/init` produces by including:
- "Start here" orientation for a new engineer
- Non-obvious gotchas and patterns
- How to work effectively with AI agents in this specific codebase
- Conventions the agent should follow and anti-patterns to avoid

This is the centerpiece output. It must be visibly better than what `/init` generates on the same repo.

### 3. Suggested Hooks
Pre-tool and post-tool hooks appropriate to the repo's actual stack:
- Python repo → ruff linting hook, type checking hook
- TypeScript repo → ESLint hook, type checking hook
- Both → DRY check hook, test runner hook
Hooks are actionable — copy-paste ready with setup instructions.

### 4. Starter Skills File
A `SKILL.md` tuned to the repo's domain and patterns. Not generic. Includes:
- How agents should navigate this specific codebase
- Key patterns used throughout (e.g. "this repo uses dependency injection extensively — always check for existing interfaces before creating new ones")
- What good output looks like for this repo's conventions

## The Demo Deliverable

**Not a live demo.** The ask is "send me something I can show my boss."

Deliverables:
1. A deployed Vite UI showing the full onboarding package for both target repos — navigable, readable, impressive
2. A short walkthrough video (Loom) explaining what was built and why
3. The GitHub repo (public) showing the pipeline code

The deployed UI is the artifact. The video is the narrative. The repo is the proof.

## What Makes This Different from `/init`

| | `/init` | Eureka |
|---|---|---|
| Input | Current repo in Claude Code session | Any GitHub URL |
| Process | Single-pass, single model | Multi-agent pipeline, specialized agents |
| Architecture overview | Implicit in CLAUDE.md | Explicit, standalone document |
| CLAUDE.md | Generic structure | Opinionated, onboarding-focused |
| Hooks | None | Stack-appropriate, copy-paste ready |
| Skills file | None | Repo-specific, agent-tuned |
| Output format | Markdown file | Interactive deployed UI |
| AI-first orientation | None | Core purpose |

## The Audience

Drew at Gauntlet AI, forwarding to his boss and hiring partners. They are technical. They will look at the pipeline code. They will read the output and know immediately whether it's generic or genuinely insightful. The bar is: would I actually use this output if I were onboarding to this repo?

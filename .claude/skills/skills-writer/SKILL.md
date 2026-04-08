---
name: skills-writer
description: Generates installable Claude Code skill files for a codebase. Use when producing task-specific instruction sets (add-endpoint, write-migration, etc.) based on repo patterns and conventions.
---

# Skills Writer Skill — Generating Installable Claude Code Skills

You are the Skills Writer agent. Your job is to produce a set of installable Claude Code skill files for this specific codebase. Each skill is a task-specific instruction set that lives in `.claude/skills/skill-name/SKILL.md`.

## What Is a Skill?

A Claude Code skill is a markdown file that teaches an agent how to perform a specific task in a specific codebase. Skills are stored in `.claude/skills/` and are invoked by name when an engineer (or agent) needs to perform that task.

Skill files follow the [Agent Skills specification](https://agentskills.io/specification.md).

## Your Job

Analyze the codebase (from the Explorer, Architect, and CLAUDE.md outputs in memory) and produce 3-5 skills that cover the most common tasks an engineer would perform in this repo.

### How to Choose Skills

Pick tasks that are:
- **Frequent** — things engineers do weekly, not once-a-year
- **Non-obvious** — the steps involve repo-specific knowledge, not just generic coding
- **Error-prone** — tasks where skipping a step causes problems (missed test, broken types, etc.)

Good skill examples for different repo types:
- **API repo**: `add-endpoint`, `add-middleware`, `update-schema`
- **Library repo**: `add-public-api`, `write-docs-example`, `add-plugin`
- **Monorepo**: `add-package`, `cross-package-change`, `update-shared-types`

Bad skill examples (too generic):
- `write-tests` (unless the repo has a very specific test pattern)
- `fix-bug` (not specific enough to be useful)
- `refactor-code` (no repo-specific content possible)

## Output Format

Produce your output as a series of skill files, each clearly delimited. Use this exact format:

```markdown
---
name: INSERT_SKILL_NAME
description: INSERT_SKILL_DESCRIPTION
---

=== skill: INSERT_SKILL_NAME ===

# Skill Name

Description of when to use this skill — the trigger.

## Steps

1. Step one — specific, actionable, referencing actual files and patterns in this repo
2. Step two
3. ...

## Example

A concrete example showing what the input and output of this skill looks like.

## References

- `path/to/relevant/file.py` — why this file matters for this task
```

Repeat for each skill. The `skill-name` after `=== skill:` becomes the directory name (e.g., `.claude/skills/add-endpoint/SKILL.md`).

## Rules

- **Every step must reference actual files, directories, or patterns from this repo.** No generic instructions.
- **Steps must be ordered correctly.** If step 3 depends on step 2, say so.
- **Include the "why" for non-obvious steps.** "Register the route in `src/app.py` — routes are not auto-discovered, missing this step means your endpoint won't be reachable."
- **Keep each skill to 5-10 steps.** If it's more complex, break it into separate skills.
- **Name skills with kebab-case verbs**: `add-endpoint`, `write-migration`, `update-plugin`.

## Input

You receive all previous agent outputs from the memory file: Explorer (summary, stack, directory tree), Architect (overview, key abstractions), CLAUDE.md (commands, gotchas, patterns). Use these to identify the right skills and fill them with repo-specific detail.

You also have two tools for accessing source code:

- **`search_repo(query, n_results=5)`** — Semantic search across the repo. Use to find patterns and conventions: "how routes are defined", "how tests are structured", "how plugins are registered".
- **`get_file(path)`** — Retrieve a specific file by path. Supports partial paths.

**Strategy**: Use these tools to verify the specific file paths, function names, and patterns you reference in skill steps. Every step in a skill should point to real code — use the tools to confirm before writing.

## What NOT to Do

- Do not produce a single monolithic SKILL.md. Produce multiple discrete skills.
- Do not write generic skills that could apply to any repo.
- Do not repeat content from the CLAUDE.md. Skills are for task execution, CLAUDE.md is for orientation.
- Do not describe what skills are or why they exist. Just produce the skill files.

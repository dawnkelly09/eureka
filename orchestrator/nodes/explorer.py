"""Explorer node — ingests a repo via gitingest and populates Ghost RAG."""

from __future__ import annotations

import json
import re

from gitingest import ingest, ingest_async
from langsmith import traceable

from orchestrator.config import logger
from orchestrator.state import EurekaState
from orchestrator.memory import append_memory
from orchestrator.audit import audit_log
from orchestrator.ghost_rag import init_ghost_rag

# Pre-tool filters: things we never want on the tree OR in ChromaDB
EXCLUDE_PATTERNS = {
    "docs/*/docs/*",        # translated docs
    "docs/*/llm-prompt*",
    "docs/*/mkdocs*",
    "*.lock",
    "*.min.js",
    "*.min.css",
    "*.snap",               # jest snapshots
    "*.fixture.*",
    "playground/*",
    "examples/*",
    "benchmark/*",
    "benchmarks/*",
    ".changeset/*",
    "CHANGELOG*",
}

MAX_FILE_SIZE = 512 * 1024  # 512 KB per file

# Config files to extract for stack detection (before ChromaDB indexing)
STACK_CONFIG_FILES = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "Cargo.toml", "go.mod",
    "tsconfig.json", "pnpm-workspace.yaml",
}


def _extract_repo_name(repo_url: str) -> str:
    """Extract repo name from a GitHub URL."""
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


def _detect_stack_from_tree_and_configs(tree: str, config_contents: dict[str, str]) -> dict:
    """Detect technology stack from the directory tree and config file contents.

    Uses tree for file existence checks, config contents for deeper detection.
    """
    stack = {
        "languages": [],
        "framework": None,
        "package_manager": None,
        "test_framework": None,
        "linter": None,
        "type_checker": None,
        "ci": None,
    }

    # Python detection
    has_pyproject = "pyproject.toml" in tree
    has_setup_py = "setup.py" in tree
    has_requirements = "requirements.txt" in tree

    if has_pyproject or has_setup_py or has_requirements:
        stack["languages"].append("Python")
        toml = config_contents.get("pyproject.toml", "")
        if toml:
            if "poetry" in toml:
                stack["package_manager"] = "poetry"
            elif "hatch" in toml:
                stack["package_manager"] = "hatch"
            elif "flit" in toml:
                stack["package_manager"] = "flit"
            else:
                stack["package_manager"] = "pip"
            if "fastapi" in toml.lower():
                stack["framework"] = "FastAPI"
            elif "django" in toml.lower():
                stack["framework"] = "Django"
            elif "flask" in toml.lower():
                stack["framework"] = "Flask"
            if "pytest" in toml:
                stack["test_framework"] = "pytest"
            if "ruff" in toml:
                stack["linter"] = "ruff"
            elif "flake8" in toml:
                stack["linter"] = "flake8"
            if "mypy" in toml:
                stack["type_checker"] = "mypy"
            elif "pyright" in toml:
                stack["type_checker"] = "pyright"
        else:
            stack["package_manager"] = "pip"

    # TypeScript/JavaScript detection
    pkg_text = config_contents.get("package.json", "")
    if "package.json" in tree:
        if "TypeScript" not in stack["languages"] and "JavaScript" not in stack["languages"]:
            if "typescript" in pkg_text.lower():
                stack["languages"].append("TypeScript")
            else:
                stack["languages"].append("JavaScript")
            try:
                pkg = json.loads(pkg_text)
                all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "vite" in all_deps:
                    stack["framework"] = stack["framework"] or "Vite"
                elif "next" in all_deps:
                    stack["framework"] = stack["framework"] or "Next.js"
                elif "react" in all_deps and not stack["framework"]:
                    stack["framework"] = "React"
                if "vitest" in all_deps:
                    stack["test_framework"] = stack["test_framework"] or "vitest"
                elif "jest" in all_deps:
                    stack["test_framework"] = stack["test_framework"] or "jest"
                if "eslint" in all_deps:
                    stack["linter"] = stack["linter"] or "eslint"
            except (json.JSONDecodeError, TypeError):
                pass

        if "pnpm-workspace.yaml" in tree or "pnpm-lock.yaml" in tree:
            stack["package_manager"] = stack["package_manager"] or "pnpm"
        elif "yarn.lock" in tree:
            stack["package_manager"] = stack["package_manager"] or "yarn"
        else:
            stack["package_manager"] = stack["package_manager"] or "npm"

    # Rust detection
    if "Cargo.toml" in tree:
        stack["languages"].append("Rust")

    # Go detection
    if "go.mod" in tree:
        stack["languages"].append("Go")

    # TypeScript type checker
    if "tsconfig.json" in tree:
        stack["type_checker"] = stack["type_checker"] or "tsc"

    # CI detection
    if ".github/workflows/" in tree or "workflows/" in tree:
        stack["ci"] = "GitHub Actions"

    return stack


def _split_content(content: str) -> list[tuple[str, str]]:
    """Split gitingest content artifact into (filepath, file_content) pairs."""
    files = []
    parts = content.split("================================================\n")
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith("FILE: "):
            filepath = part.split("\n", 1)[0].replace("FILE: ", "").strip()
            file_content = parts[i + 1] if i + 1 < len(parts) else ""
            files.append((filepath, file_content))
            i += 2
        else:
            i += 1
    return files


def _extract_config_contents(
    all_files: list[tuple[str, str]],
) -> dict[str, str]:
    """Pull config file contents out for stack detection."""
    configs = {}
    for path, content in all_files:
        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        if filename in STACK_CONFIG_FILES:
            configs[filename] = content
    return configs


@traceable(run_type="chain", name="explorer_node")
async def run_explorer(state: EurekaState) -> EurekaState:
    """Ingest a repo via gitingest and populate Ghost RAG."""
    run_id = state["run_id"]
    repo_url = state["repo_url"]
    repo_name = _extract_repo_name(repo_url)

    audit_log(run_id, "explorer_start", repo_url)
    logger.info(f"[{run_id}] Ingesting {repo_url} via gitingest...")

    # 1. Run gitingest with pre-tool filters
    # Use ingest_async when inside an existing event loop (FastAPI),
    # fall back to sync ingest for standalone testing
    try:
        import asyncio
        asyncio.get_running_loop()
        summary, tree, content = await ingest_async(
            repo_url,
            exclude_patterns=EXCLUDE_PATTERNS,
            max_file_size=MAX_FILE_SIZE,
        )
    except RuntimeError:
        summary, tree, content = ingest(
            repo_url,
            exclude_patterns=EXCLUDE_PATTERNS,
            max_file_size=MAX_FILE_SIZE,
        )

    logger.info(f"[{run_id}] gitingest complete: {summary.strip()}")

    # 2. Split content and extract config files for stack detection
    all_files = _split_content(content)
    config_contents = _extract_config_contents(all_files)

    # 3. Detect stack from tree + config contents
    stack = _detect_stack_from_tree_and_configs(tree, config_contents)
    logger.info(f"[{run_id}] Stack detected: {json.dumps(stack)}")

    # 4. Populate Ghost RAG (post-process filtering of tests happens inside)
    doc_count = init_ghost_rag(run_id, content)

    # 5. Write summary + tree to memory (not file contents — agents use Ghost RAG)
    memory_content = (
        f"## Project Overview\n{repo_url}\nRepo name: {repo_name}\n\n"
        f"## Stack\n```json\n{json.dumps(stack, indent=2)}\n```\n\n"
        f"## {summary}\n\n"
        f"## {tree}\n\n"
        f"*{doc_count} source files indexed in Ghost RAG — "
        f"use `search_repo` and `get_file` tools to access file contents.*"
    )
    append_memory(run_id, "Explorer", memory_content)

    audit_log(run_id, "explorer_done", f"{doc_count} files indexed")

    return {
        **state,
        "repo_name": repo_name,
        "repo_structure": memory_content,
        "stack_detected": stack,
        "current_node": "explorer",
    }


# Allow standalone testing
if __name__ == "__main__":
    import asyncio
    import sys
    import uuid

    from orchestrator.memory import init_memory

    if len(sys.argv) < 2:
        print("Usage: python -m orchestrator.nodes.explorer <github_url>")
        sys.exit(1)

    url = sys.argv[1]
    rid = str(uuid.uuid4())[:8]
    init_memory(rid, url)

    initial_state: EurekaState = {
        "run_id": rid,
        "repo_url": url,
        "repo_name": "",
        "memory_file": f"memory/{rid}.md",
        "repo_structure": None,
        "stack_detected": None,
        "architecture_overview": None,
        "claude_md": None,
        "hooks": None,
        "skills_file": None,
        "current_node": "start",
        "error": None,
    }

    result = asyncio.run(run_explorer(initial_state))
    print(f"\nRun ID: {rid}")
    print(f"Repo: {result['repo_name']}")
    print(f"Stack: {json.dumps(result['stack_detected'], indent=2)}")
    print(f"\nMemory file: memory/{rid}.md")

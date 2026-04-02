"""Explorer node — clones a repo and produces a structured summary."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from langsmith import traceable

from orchestrator.config import CLONE_DIR, MAX_FILES_PER_RUN, MAX_LINES_PER_FILE, logger
from orchestrator.state import EurekaState
from orchestrator.memory import append_memory
from orchestrator.audit import audit_log


# Files to read first, in priority order
PRIORITY_FILES = [
    "README.md", "README.rst",
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "requirements.txt", "poetry.lock", "Cargo.toml", "go.mod",
    "tsconfig.json", "vite.config.ts", "vite.config.js",
    "webpack.config.js", "rollup.config.js",
    ".eslintrc.json", ".eslintrc.js", "eslint.config.js",
    "jest.config.js", "jest.config.ts", "vitest.config.ts",
    "Makefile", "justfile",
    ".github/workflows/ci.yml", ".github/workflows/ci.yaml",
    ".github/workflows/test.yml", ".github/workflows/test.yaml",
]

# Directories that reveal architecture (explore one level deep)
KEY_DIRS = [
    "src", "lib", "app", "packages", "crates",
    "tests", "test", "__tests__",
    "docs",
]

# Files to skip
SKIP_PATTERNS = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Cargo.lock", ".gitignore", ".gitattributes", "LICENSE", "LICENSE.md",
    "CHANGELOG.md", "CHANGES.md", "HISTORY.md",
}


def _clean_readme(text: str) -> str:
    """Strip visual chrome from README content to keep only useful prose.

    Removes: HTML badge/image blocks, sponsor sections, testimonial divs,
    centered alignment wrappers, and HTML comments. Keeps: actual description,
    feature lists, install instructions, usage examples.
    """
    # Remove HTML comments (<!-- sponsors --> blocks, etc.)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # Remove <p align="center"> blocks (badges, logos)
    text = re.sub(r'<p\s+align="center">.*?</p>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove standalone <img> tags (badges, sponsor logos)
    text = re.sub(r'<img\s[^>]*>', '', text, flags=re.IGNORECASE)

    # Remove <a> tags that only wrap images (sponsor links) — keep <a> with text content
    text = re.sub(r'<a\s[^>]*>\s*</a>', '', text, flags=re.IGNORECASE)

    # Remove <div> blocks (testimonial attribution, styling wrappers)
    text = re.sub(r'<div[^>]*>.*?</div>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Strip all remaining HTML tags, keeping text content inside them
    text = re.sub(r'<[^>]+>', '', text)

    # Remove markdown badge images: [![alt](badge-url)](link) and ![alt](badge-url)
    text = re.sub(r'\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)', '', text)
    text = re.sub(r'!\[[^\]]*\]\(https?://[^)]*(?:badge|shield|img\.shields)[^)]*\)', '', text)

    # Cut entire sections that are noise for downstream agents
    noise_sections = {'sponsors', 'opinions', 'testimonials', 'backers', 'funding',
                      'contributors', 'acknowledgements', 'acknowledgments'}
    lines = text.splitlines()
    cleaned_lines = []
    skipping = False
    skip_level = 0  # header level that started the skip (e.g. 2 for ##)
    for line in lines:
        header_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if header_match:
            level = len(header_match.group(1))
            section_name = header_match.group(2).strip().lower()
            if section_name in noise_sections:
                skipping = True
                skip_level = level
                continue
            elif skipping and level <= skip_level:
                # Hit a same-or-higher-level header — stop skipping
                skipping = False
        if not skipping:
            cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # Collapse runs of 3+ blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _read_file_truncated(path: Path, max_lines: int = MAX_LINES_PER_FILE) -> tuple[str, bool]:
    """Read a file, truncating at max_lines. Returns (content, was_truncated)."""
    try:
        lines = path.read_text(errors="replace").splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]), True
        return "\n".join(lines), False
    except Exception as e:
        return f"[Error reading file: {e}]", False


def _clone_repo(repo_url: str) -> Path:
    """Shallow clone a GitHub repo. Returns the clone path."""
    CLONE_DIR.mkdir(parents=True, exist_ok=True)
    # Extract repo name from URL
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_path = CLONE_DIR / repo_name

    if clone_path.exists():
        shutil.rmtree(clone_path)

    subprocess.run(
        ["git", "clone", "--depth=1", repo_url, str(clone_path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return clone_path


def _get_dir_listing(path: Path, depth: int = 0, max_depth: int = 2, _remaining_depth: int = None) -> list[str]:
    """Get a directory listing up to max_depth levels."""
    if _remaining_depth is None:
        _remaining_depth = max_depth
    entries = []
    # Directories to only show top-level contents for
    shallow_dirs = {"docs", "doc", "examples", "benchmarks", "scripts", ".github"}
    skip_dirs = {"node_modules", "__pycache__", ".git", "dist", "build", ".tox",
                 ".mypy_cache", "docs_src", ".eggs", "htmlcov", ".pytest_cache",
                 "playground"}
    try:
        for item in sorted(path.iterdir()):
            if item.name.startswith(".") and item.name not in (".github",):
                continue
            if item.name in skip_dirs:
                continue
            prefix = "  " * depth
            if item.is_dir():
                # Skip template-* dirs (e.g. create-vite/template-react-ts/)
                if item.name.startswith("template-"):
                    if not any(e.startswith(f"{prefix}template-") for e in entries):
                        entries.append(f"{prefix}template-*/  (templates omitted)")
                    continue
                entries.append(f"{prefix}{item.name}/")
                if item.name in shallow_dirs:
                    child_remaining = 0  # only show immediate children
                else:
                    child_remaining = _remaining_depth - 1
                if child_remaining >= 0:
                    entries.extend(_get_dir_listing(item, depth + 1, max_depth, child_remaining))
            else:
                entries.append(f"{prefix}{item.name}")
    except PermissionError:
        pass
    return entries


def _detect_stack(clone_path: Path) -> dict:
    """Detect the technology stack from config files."""
    stack = {
        "languages": [],
        "framework": None,
        "package_manager": None,
        "test_framework": None,
        "linter": None,
        "type_checker": None,
        "ci": None,
    }

    # Check for Python
    if (clone_path / "pyproject.toml").exists() or (clone_path / "setup.py").exists() or (clone_path / "requirements.txt").exists():
        stack["languages"].append("Python")
        if (clone_path / "pyproject.toml").exists():
            toml_content = (clone_path / "pyproject.toml").read_text(errors="replace")
            if "poetry" in toml_content:
                stack["package_manager"] = "poetry"
            elif "hatch" in toml_content:
                stack["package_manager"] = "hatch"
            elif "flit" in toml_content:
                stack["package_manager"] = "flit"
            else:
                stack["package_manager"] = "pip"
            if "fastapi" in toml_content.lower():
                stack["framework"] = "FastAPI"
            elif "django" in toml_content.lower():
                stack["framework"] = "Django"
            elif "flask" in toml_content.lower():
                stack["framework"] = "Flask"
            if "pytest" in toml_content:
                stack["test_framework"] = "pytest"
            if "ruff" in toml_content:
                stack["linter"] = "ruff"
            elif "flake8" in toml_content:
                stack["linter"] = "flake8"
            if "mypy" in toml_content:
                stack["type_checker"] = "mypy"
            elif "pyright" in toml_content:
                stack["type_checker"] = "pyright"
        else:
            stack["package_manager"] = "pip"

    # Check for TypeScript/JavaScript
    if (clone_path / "package.json").exists():
        if "TypeScript" not in stack["languages"] and "JavaScript" not in stack["languages"]:
            pkg_text = (clone_path / "package.json").read_text(errors="replace")
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
            except json.JSONDecodeError:
                pass

        if (clone_path / "pnpm-workspace.yaml").exists() or (clone_path / "pnpm-lock.yaml").exists():
            stack["package_manager"] = stack["package_manager"] or "pnpm"
        elif (clone_path / "yarn.lock").exists():
            stack["package_manager"] = stack["package_manager"] or "yarn"
        else:
            stack["package_manager"] = stack["package_manager"] or "npm"

    # Check for tsconfig at root or in sub-packages (monorepos)
    has_tsconfig = (clone_path / "tsconfig.json").exists()
    if not has_tsconfig:
        for sub in ("packages", "apps", "libs"):
            sub_path = clone_path / sub
            if sub_path.exists():
                has_tsconfig = any((sub_path / d / "tsconfig.json").exists()
                                   for d in sub_path.iterdir() if d.is_dir())
                if has_tsconfig:
                    break
    if has_tsconfig:
        stack["type_checker"] = stack["type_checker"] or "tsc"

    # CI detection
    gh_workflows = clone_path / ".github" / "workflows"
    if gh_workflows.exists():
        stack["ci"] = "GitHub Actions"

    return stack


def _find_entry_points(clone_path: Path, stack: dict) -> list[str]:
    """Find likely entry point files."""
    candidates = [
        "src/main.py", "src/app.py", "main.py", "app.py", "app/__init__.py",
        "src/index.ts", "src/main.ts", "src/index.js", "src/main.js",
        "index.ts", "index.js", "src/node/index.ts", "src/client/index.ts",
    ]
    found = []
    for c in candidates:
        if (clone_path / c).exists():
            found.append(c)

    # Check package.json for main/entry
    pkg_path = clone_path / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(errors="replace"))
            for field in ("main", "module", "exports"):
                if field in pkg and isinstance(pkg[field], str):
                    if (clone_path / pkg[field]).exists():
                        found.append(pkg[field])
        except (json.JSONDecodeError, TypeError):
            pass

    # Check pyproject.toml for scripts
    pyproject = clone_path / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(errors="replace")
        if "[project.scripts]" in content or "[tool.poetry.scripts]" in content:
            found.append("pyproject.toml (has CLI entry points)")

    return list(dict.fromkeys(found))  # dedupe preserving order


def _find_source_dirs(clone_path: Path, repo_name: str) -> list[str]:
    """Find directories that contain source code."""
    candidates = ["src", "lib", "app", "packages", repo_name, repo_name.replace("-", "_")]
    found = []
    for c in candidates:
        if (clone_path / c).exists() and (clone_path / c).is_dir():
            found.append(c)
    # Also look for any top-level dir with an __init__.py (Python package)
    for item in clone_path.iterdir():
        if item.is_dir() and (item / "__init__.py").exists() and item.name not in found:
            if item.name not in ("tests", "test", "docs", "scripts", "examples", "benchmarks"):
                found.append(item.name)
    return found


def _sample_key_files(clone_path: Path, stack: dict, entry_points: list[str], already_read: set[str], repo_name: str = "") -> list[str]:
    """Pick representative source files to sample."""
    samples = []
    src_dirs = _find_source_dirs(clone_path, repo_name)

    for src_dir in src_dirs:
        src_path = clone_path / src_dir
        if not src_path.exists():
            continue
        # Find source files (not tests, not configs)
        for ext in ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx"):
            found = list(src_path.rglob(ext))
            # Filter out tests, boilerplate, templates, and generated files
            noise_path_parts = {"__pycache__", "node_modules", "template-",
                                "playground", "examples", "fixtures", "dist"}
            found = [
                f for f in found
                if not any(p in str(f) for p in noise_path_parts)
                and "test" not in f.name.lower()
                and ".d.ts" not in f.name
            ]
            # Sort by size (medium-sized files are usually most informative)
            found.sort(key=lambda f: abs(f.stat().st_size - 2000))
            for f in found[:3]:
                rel = str(f.relative_to(clone_path))
                if rel not in already_read:
                    samples.append(rel)
                    if len(samples) >= 5:
                        return samples

    # Also grab a test file
    for test_dir in ["tests", "test", "__tests__"]:
        test_path = clone_path / test_dir
        if test_path.exists():
            for ext in ("*.py", "*.ts", "*.js"):
                test_files = list(test_path.rglob(ext))
                test_files = [f for f in test_files if "__pycache__" not in str(f)]
                if test_files:
                    rel = str(test_files[0].relative_to(clone_path))
                    if rel not in already_read:
                        samples.append(rel)
                    break

    return samples[:5]


@traceable(run_type="chain", name="explorer_node")
def run_explorer(state: EurekaState) -> EurekaState:
    """Clone a repo, analyze it, and produce a structured summary."""
    run_id = state["run_id"]
    repo_url = state["repo_url"]

    audit_log(run_id, "explorer_start", repo_url)

    # Clone
    logger.info(f"Cloning {repo_url}...")
    clone_path = _clone_repo(repo_url)
    repo_name = clone_path.name
    logger.info(f"Cloned to {clone_path}")

    files_read = 0
    already_read: set[str] = set()
    file_summaries: list[str] = []

    def read_and_record(rel_path: str) -> str | None:
        nonlocal files_read
        if files_read >= MAX_FILES_PER_RUN:
            return None
        if rel_path in already_read:
            return None
        full_path = clone_path / rel_path
        if not full_path.exists() or not full_path.is_file():
            return None
        content, truncated = _read_file_truncated(full_path)
        # Clean READMEs — strip badges, sponsors, HTML chrome
        if rel_path.lower().startswith("readme"):
            content = _clean_readme(content)
        already_read.add(rel_path)
        files_read += 1
        trunc_note = " (truncated)" if truncated else ""
        file_summaries.append(f"### {rel_path}{trunc_note}\n```\n{content}\n```")
        return content

    # 1. Priority files
    for pf in PRIORITY_FILES:
        if files_read >= MAX_FILES_PER_RUN:
            break
        read_and_record(pf)

    # 2. Detect stack
    stack = _detect_stack(clone_path)

    # 3. Directory structure
    dir_listing = _get_dir_listing(clone_path, max_depth=2)

    # 4. Entry points
    entry_points = _find_entry_points(clone_path, stack)
    for ep in entry_points:
        if not ep.endswith(")"):  # skip notes like "pyproject.toml (has CLI entry points)"
            read_and_record(ep)

    # 5. Sample key files
    samples = _sample_key_files(clone_path, stack, entry_points, already_read, repo_name)
    for s in samples:
        read_and_record(s)

    # 6. Check for monorepo
    monorepo_info = ""
    for mono_dir in ["packages", "crates", "apps", "libs"]:
        mono_path = clone_path / mono_dir
        if mono_path.exists() and mono_path.is_dir():
            sub_packages = [d.name for d in sorted(mono_path.iterdir()) if d.is_dir() and not d.name.startswith(".")]
            if sub_packages:
                monorepo_info += f"\n**{mono_dir}/**: {', '.join(sub_packages)}"

    # Build the summary
    summary_parts = [
        f"## Project Overview\n{repo_url}\nRepo name: {repo_name}\n",
        f"## Stack\n```json\n{json.dumps(stack, indent=2)}\n```\n",
        f"## Directory Structure\n```\n" + "\n".join(dir_listing[:100]) + "\n```\n",
    ]

    if monorepo_info:
        summary_parts.append(f"## Monorepo Structure{monorepo_info}\n")

    if entry_points:
        summary_parts.append(f"## Entry Points\n" + "\n".join(f"- `{ep}`" for ep in entry_points) + "\n")

    summary_parts.append(f"## Files Read ({files_read} total)\n" + "\n".join(file_summaries))

    summary = "\n".join(summary_parts)

    # Write to memory
    append_memory(run_id, "Explorer", summary)

    # Cleanup clone
    shutil.rmtree(clone_path, ignore_errors=True)

    audit_log(run_id, "explorer_done", f"{files_read} files read")

    return {
        **state,
        "repo_name": repo_name,
        "repo_structure": summary,
        "stack_detected": stack,
        "current_node": "explorer",
    }


# Allow standalone testing
if __name__ == "__main__":
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

    result = run_explorer(initial_state)
    print(f"\nRun ID: {rid}")
    print(f"Repo: {result['repo_name']}")
    print(f"Stack: {json.dumps(result['stack_detected'], indent=2)}")
    print(f"\nMemory file: memory/{rid}.md")

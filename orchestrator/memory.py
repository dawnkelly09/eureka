"""Memory file helpers — init and append-only writes."""

from datetime import datetime, timezone
from pathlib import Path

from langsmith import traceable

from orchestrator.config import MEMORY_DIR, TEMPLATE_PATH
from orchestrator.audit import audit_log


@traceable(run_type="tool", name="init_memory")
def init_memory(run_id: str, repo_url: str) -> Path:
    path = MEMORY_DIR / f"{run_id}.md"
    if path.exists():
        return path
    MEMORY_DIR.mkdir(exist_ok=True)
    template = TEMPLATE_PATH.read_text()
    content = template.replace("{{RUN_ID}}", run_id).replace("{{REPO_URL}}", repo_url)
    path.write_text(content)
    audit_log(run_id, "memory_init", str(path))
    return path


@traceable(run_type="tool", name="append_memory")
def append_memory(run_id: str, section: str, content: str) -> None:
    path = MEMORY_DIR / f"{run_id}.md"
    ts = datetime.now(timezone.utc).isoformat()
    text = path.read_text()
    marker = f"## {section}"
    if marker in text:
        text = text.replace(
            f"{marker}\n_pending_",
            f"{marker}\n_{ts}_\n\n{content}",
        )
        path.write_text(text)
    else:
        with path.open("a") as f:
            f.write(f"\n{marker}\n_{ts}_\n\n{content}\n")
    audit_log(run_id, f"memory_append:{section}", f"{len(content)} chars")

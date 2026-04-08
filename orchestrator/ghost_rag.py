"""Ghost RAG — ephemeral per-run vector store for repo content.

Creates a ChromaDB collection from gitingest output, provides semantic
and path-based queries, and destroys itself when the pipeline finishes.
"""

import re

import chromadb
from langsmith import traceable

from orchestrator.config import logger

# Singleton ephemeral client — in-memory only, no disk persistence
_client = chromadb.EphemeralClient()

# Patterns that identify test files (excluded from ChromaDB, kept in tree)
_TEST_PATH_RE = re.compile(
    r"tests?/|__tests__/|\.test\.|\.spec\.|test_.*\.py|_test\.go|_test\.rs"
)


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


@traceable(run_type="tool", name="init_ghost_rag")
def init_ghost_rag(run_id: str, content: str) -> int:
    """Populate a ChromaDB collection from gitingest content.

    Splits content by file, filters out test files, indexes the rest.
    Returns the number of documents indexed.
    """
    all_files = _split_content(content)

    # Post-process: keep test files out of the vector store
    source_files = [(p, c) for p, c in all_files if not _TEST_PATH_RE.search(p)]

    if not source_files:
        logger.warning(f"[{run_id}] No source files to index after filtering")
        return 0

    collection = _client.get_or_create_collection(
        name=run_id,
        metadata={"hnsw:space": "cosine"},
    )

    # Batch add — ChromaDB handles embedding via default model
    collection.add(
        ids=[f"doc-{i}" for i in range(len(source_files))],
        documents=[content for _, content in source_files],
        metadatas=[{"path": path} for path, _ in source_files],
    )

    logger.info(f"[{run_id}] Ghost RAG initialized: {len(source_files)} files indexed")
    return len(source_files)


@traceable(run_type="tool", name="query_ghost_rag")
def query_ghost_rag(run_id: str, query: str, n_results: int = 5) -> list[dict]:
    """Semantic search against the repo collection.

    Returns list of {path, content, distance} dicts, ranked by relevance.
    """
    try:
        collection = _client.get_collection(name=run_id)
    except Exception:
        logger.error(f"[{run_id}] Ghost RAG collection not found")
        return []

    results = collection.query(query_texts=[query], n_results=n_results)

    out = []
    for i in range(len(results["ids"][0])):
        out.append({
            "path": results["metadatas"][0][i]["path"],
            "content": results["documents"][0][i],
            "distance": results["distances"][0][i],
        })
    return out


@traceable(run_type="tool", name="query_ghost_rag_by_path")
def query_ghost_rag_by_path(run_id: str, path_pattern: str) -> list[dict]:
    """Direct lookup by file path substring.

    Searches metadata for paths containing the pattern.
    Returns list of {path, content} dicts.
    """
    try:
        collection = _client.get_collection(name=run_id)
    except Exception:
        logger.error(f"[{run_id}] Ghost RAG collection not found")
        return []

    # ChromaDB doesn't support substring matching on metadata,
    # so we fetch all and filter in Python (~500 files, trivial cost)
    all_docs = collection.get(include=["documents", "metadatas"])

    pattern_lower = path_pattern.lower()
    out = []
    for i in range(len(all_docs["ids"])):
        path = all_docs["metadatas"][i]["path"]
        if pattern_lower in path.lower():
            out.append({
                "path": path,
                "content": all_docs["documents"][i],
            })
    return out


@traceable(run_type="tool", name="destroy_ghost_rag")
def destroy_ghost_rag(run_id: str) -> None:
    """Delete the collection for a completed run."""
    try:
        _client.delete_collection(name=run_id)
        logger.info(f"[{run_id}] Ghost RAG destroyed")
    except Exception:
        logger.warning(f"[{run_id}] Ghost RAG collection not found for cleanup")

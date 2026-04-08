Plan: Replace Explorer with gitingest + Ghost RAG

Context

The current explorer node (orchestrator/nodes/explorer.py) clones a repo and curates ~50 files with a hardcoded priority system. This is
fragile — the agent picks what it thinks matters and downstream agents are stuck with that selection. We're replacing it with:

1.  gitingest for repo ingestion — produces summary, directory tree, and file contents
2.  ChromaDB as an ephemeral per-run vector store ("Ghost RAG") — downstream agents query for what they actually need instead of getting a
    pre-curated dump
3.  An in-process MCP server so agents can search the vector store via tool calls

This reduces tokens in the memory file (only summary + tree go there), gives agents access to the full repo on demand, and eliminates the
"game of telephone" where the explorer's curation choices constrain everything downstream.

---

Step 1: Add dependencies

File: requirements.txt

Add:

- gitingest — repo ingestion
- chromadb — local vector store (uses all-MiniLM-L6-v2 embeddings by default, no API calls)

Both are already pip-installable. ChromaDB runs fully local.

---

Step 2: Create the Ghost RAG module

New file: orchestrator/ghost_rag.py

Responsibilities:

- init*ghost_rag(run_id, content) — Takes the gitingest content string, splits on FILE: delimiters, creates a ChromaDB ephemeral collection
  named after the run_id. Each document = one file's content, metadata = {"path": "relative/file/path"}. Post-process filter: exclude files
  matching test path patterns (tests/, **tests**/, *.test.*, *.spec.*, test*\*.py) before indexing.
- query_ghost_rag(run_id, query, n_results=5) — Semantic search against the collection. Returns file paths + content snippets.
- query_ghost_rag_by_path(run_id, path_pattern) — Direct lookup by file path (metadata filter). For when agents know exactly what file they
  want.
- destroy_ghost_rag(run_id) — Deletes the collection. Called after pipeline completes.

Uses ChromaDB's ephemeral client (chromadb.EphemeralClient()) — in-memory only, no disk persistence needed.

---

Step 3: Create the MCP server for agent access

New file: orchestrator/mcp_tools.py

Uses claude-agent-sdk's built-in create_sdk_mcp_server() and @tool decorator to define an in-process MCP server. No separate process needed.

Tools exposed to agents:

- search_repo(query: str, n_results: int = 5) — Semantic search. "Find authentication middleware", "find the main entry point". Returns
  matching file paths and content.
- get_file(path: str) — Direct file retrieval by path. Agent sees src/auth/middleware.py in the tree and wants to read it.

The server is created per-run with the run_id baked in, so each agent session queries the correct collection.

---

Step 4: Rewrite the explorer node

File: orchestrator/nodes/explorer.py

Replace the current clone-and-curate logic with:

1.  Call gitingest.ingest() with pre-tool filters:

- exclude_patterns: translated docs, changelogs, playgrounds, examples, benchmarks, snapshots, changesets
- max_file_size: 512 KB

2.  Post-process: split content, filter test files out before ChromaDB indexing
3.  Call init_ghost_rag(run_id, filtered_content) to populate the vector store
4.  Append only summary + tree to the memory file's Explorer section
5.  Do a lightweight stack detection pass on the tree (scan for pyproject.toml, package.json, tsconfig.json, etc. in the tree string — same
    signals the current explorer uses, just reading the tree instead of opening files)
6.  Return updated state with repo_name, repo_structure (summary + tree), stack_detected

The explorer skill file (.claude/skills/explorer/SKILL.md) stays as-is — it already says "intelligence lives in the downstream agents."

---

Step 5: Update agent_runner to pass MCP server

File: orchestrator/agent_runner.py

Modify run_agent() to:

1.  Accept an optional mcp_server parameter
2.  Pass it to ClaudeAgentOptions via mcp_servers={"ghost-rag": mcp_server}
3.  Add search_repo and get_file to the allowed_tools list alongside Read, Glob, Grep

The MCP server instance is created once per run and passed to each agent node.

---

Step 6: Update the pipeline DAG

File: orchestrator/graph.py

- Create the MCP server after the explorer node completes (the explorer populates Ghost RAG)
- Pass the MCP server through state or create it in each agent node wrapper
- Add a cleanup step after the Skills node: call destroy_ghost_rag(run_id)

File: orchestrator/state.py

- Remove stack_detected if we fold stack info into the tree-based summary, OR keep it if downstream agents reference it directly (need to
  check agent prompts — hooks agent uses "detected stack" explicitly, so keep it)

---

Step 7: Update downstream agent skill files

Files: .claude/skills/architect/SKILL.md, claude-md-writer/SKILL.md, hooks-generator/SKILL.md, skills-writer/SKILL.md

Update the "Input" section of each skill to tell agents:

- Memory file now contains summary + directory tree (not file contents)
- They have two new tools: search_repo for semantic search and get_file for direct file access
- Strategy: scan the tree to identify what you need, then use get_file or search_repo to pull specific content

This is a prompt change, not a code change. The agents' actual behavior instructions stay the same.

---

Step 8: Clean up

- Delete the clone/cleanup logic from explorer (no more /tmp/eureka-clones)
- Remove MAX_FILES_PER_RUN and MAX_LINES_PER_FILE constants from config (gitingest handles its own limits)
- Remove spike directory (spike/gitingest_test/) — it served its purpose

---

Files modified (summary)

┌────────────────────────────────┬────────────────────────────────────────────────────────────┐
│ File │ Change │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ requirements.txt │ Add gitingest, chromadb │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ orchestrator/ghost_rag.py │ New — ChromaDB wrapper │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ orchestrator/mcp_tools.py │ New — In-process MCP server │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ orchestrator/nodes/explorer.py │ Rewrite — gitingest + ghost RAG init │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ orchestrator/agent_runner.py │ Add MCP server passthrough │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ orchestrator/graph.py │ Wire MCP server + cleanup step │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ orchestrator/config.py │ Remove old explorer constants, add gitingest filter config │
├────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ .claude/skills/\*/SKILL.md (x4) │ Update input docs to describe new tools │
└────────────────────────────────┴────────────────────────────────────────────────────────────┘

---

Verification

1.  Unit test the ghost_rag module: init with known content, query semantically, query by path, verify results
2.  Unit test the MCP tools: verify search_repo and get_file return expected formats
3.  Run explorer node standalone: python -m orchestrator.nodes.explorer https://github.com/fastapi/fastapi — verify memory file gets summary +
    tree, ChromaDB collection exists
4.  Run full pipeline: uvicorn orchestrator:app --reload → POST /analyze with FastAPI repo → verify all 4 artifacts generate successfully
5.  Compare output quality: Run on FastAPI and Vite, compare artifacts to previous runs stored in memory/

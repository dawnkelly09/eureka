"""MCP tools for Ghost RAG — in-process server for agent repo access.

Creates an SDK MCP server that downstream agents use to query the
ephemeral vector store. Each run gets its own server instance scoped
to its ChromaDB collection.
"""

from typing import Annotated, Optional

from claude_agent_sdk import tool, create_sdk_mcp_server
from claude_agent_sdk.types import McpSdkServerConfig

from orchestrator.ghost_rag import query_ghost_rag, query_ghost_rag_by_path


def create_ghost_rag_server(run_id: str) -> McpSdkServerConfig:
    """Create an in-process MCP server bound to a specific run's vector store."""

    @tool(
        "search_repo",
        "Semantic search across the repository source code. Use this when you need "
        "to find code by concept (e.g. 'authentication middleware', 'database connection', "
        "'route registration'). Returns the most relevant files with their full content.",
        {
            "query": Annotated[str, "What to search for — describe the concept or functionality"],
            "n_results": Annotated[Optional[int], "Number of results to return (default 5, max 20)"],
        },
    )
    async def search_repo(args: dict) -> dict:
        query = args["query"]
        n_results = min(args.get("n_results") or 5, 20)

        results = query_ghost_rag(run_id, query, n_results=n_results)

        if not results:
            return {
                "content": [{"type": "text", "text": "No results found."}],
            }

        parts = []
        for r in results:
            parts.append(f"### {r['path']}\n```\n{r['content']}\n```")

        return {
            "content": [{"type": "text", "text": "\n\n".join(parts)}],
        }

    @tool(
        "get_file",
        "Retrieve a specific file's content by its path. Use this when you can see "
        "a file in the directory tree and want to read it. Supports partial path "
        "matching (e.g. 'routing.py' will match 'src/fastapi/routing.py').",
        {
            "path": Annotated[str, "Full or partial file path to retrieve"],
        },
    )
    async def get_file(args: dict) -> dict:
        path = args["path"]

        results = query_ghost_rag_by_path(run_id, path)

        if not results:
            return {
                "content": [{"type": "text", "text": f"File not found: {path}"}],
                "is_error": True,
            }

        parts = []
        for r in results:
            parts.append(f"### {r['path']}\n```\n{r['content']}\n```")

        return {
            "content": [{"type": "text", "text": "\n\n".join(parts)}],
        }

    return create_sdk_mcp_server(
        name="ghost-rag",
        version="1.0.0",
        tools=[search_repo, get_file],
    )

"""LangGraph pipeline — sequential agent graph."""

from langgraph.graph import StateGraph, END

from orchestrator.state import EurekaState
from orchestrator.nodes.explorer import run_explorer
from orchestrator.nodes.architect import run_architect
from orchestrator.nodes.claude_md import run_claude_md
from orchestrator.nodes.hooks import run_hooks
from orchestrator.nodes.skills import run_skills
from orchestrator.ghost_rag import destroy_ghost_rag
from orchestrator.config import logger


def _wrap_sync(fn):
    """Wrap a sync function so LangGraph can call it as a node."""
    async def wrapper(state: EurekaState) -> EurekaState:
        return fn(state)
    wrapper.__name__ = fn.__name__
    return wrapper


async def _cleanup(state: EurekaState) -> EurekaState:
    """Destroy the Ghost RAG collection after the pipeline finishes."""
    destroy_ghost_rag(state["run_id"])
    logger.info(f"[{state['run_id']}] Pipeline cleanup complete")
    return state


def build_graph() -> StateGraph:
    """Build the Eureka pipeline graph."""
    graph = StateGraph(EurekaState)

    # Add nodes
    graph.add_node("explorer", run_explorer)
    graph.add_node("architect", run_architect)
    graph.add_node("claude_md", run_claude_md)
    graph.add_node("hooks", run_hooks)
    graph.add_node("skills", run_skills)
    graph.add_node("cleanup", _cleanup)

    # Sequential edges
    graph.set_entry_point("explorer")
    graph.add_edge("explorer", "architect")
    graph.add_edge("architect", "claude_md")
    graph.add_edge("claude_md", "hooks")
    graph.add_edge("hooks", "skills")
    graph.add_edge("skills", "cleanup")
    graph.add_edge("cleanup", END)

    return graph.compile()

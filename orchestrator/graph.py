"""LangGraph pipeline — sequential agent graph."""

from langgraph.graph import StateGraph, END

from orchestrator.state import EurekaState
from orchestrator.nodes.explorer import run_explorer
from orchestrator.nodes.architect import run_architect
from orchestrator.nodes.claude_md import run_claude_md
from orchestrator.nodes.hooks import run_hooks
from orchestrator.nodes.skills import run_skills


def _wrap_sync(fn):
    """Wrap a sync function so LangGraph can call it as a node."""
    async def wrapper(state: EurekaState) -> EurekaState:
        return fn(state)
    wrapper.__name__ = fn.__name__
    return wrapper


def build_graph() -> StateGraph:
    """Build the Eureka pipeline graph."""
    graph = StateGraph(EurekaState)

    # Add nodes
    graph.add_node("explorer", _wrap_sync(run_explorer))
    graph.add_node("architect", run_architect)
    graph.add_node("claude_md", run_claude_md)
    graph.add_node("hooks", run_hooks)
    graph.add_node("skills", run_skills)

    # Sequential edges
    graph.set_entry_point("explorer")
    graph.add_edge("explorer", "architect")
    graph.add_edge("architect", "claude_md")
    graph.add_edge("claude_md", "hooks")
    graph.add_edge("hooks", "skills")
    graph.add_edge("skills", END)

    return graph.compile()

"""
Graph wiring — this is the file that turns the flow diagram in your notes
into an executable LangGraph StateGraph:

START
  -> query_analysis
       - index   -> retriever -> grade -> (relevant? generate : rewrite -> retriever)
       - general -> general_llm -> END
       - search  -> web_search -> generate_from_search -> END
"""
from langgraph.graph import StateGraph, START, END

from backend.rag.state import GraphState
from backend.rag.nodes import (
    query_analysis,
    retriever_node,
    grade,
    rewrite,
    generate,
    general_llm,
    web_search_node,
    generate_from_search,
    MAX_REWRITES,
)


def route_after_analysis(state: GraphState) -> str:
    return state["route"]  # "index" | "general" | "search"


def route_after_grade(state: GraphState) -> str:
    if state.get("relevant"):
        return "generate"
    if state.get("rewrite_count", 0) >= MAX_REWRITES:
        # Safety valve: stop looping forever, answer with best-effort context
        return "generate"
    return "rewrite"


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("query_analysis", query_analysis)
    graph.add_node("retriever", retriever_node)
    graph.add_node("grade", grade)
    graph.add_node("rewrite", rewrite)
    graph.add_node("generate", generate)
    graph.add_node("general_llm", general_llm)
    graph.add_node("web_search", web_search_node)
    graph.add_node("generate_from_search", generate_from_search)

    graph.add_edge(START, "query_analysis")

    graph.add_conditional_edges(
        "query_analysis",
        route_after_analysis,
        {
            "index": "retriever",
            "general": "general_llm",
            "search": "web_search",
        },
    )

    graph.add_edge("retriever", "grade")

    graph.add_conditional_edges(
        "grade",
        route_after_grade,
        {
            "generate": "generate",
            "rewrite": "rewrite",
        },
    )

    # self-correcting loop: rewrite -> retriever -> grade -> ...
    graph.add_edge("rewrite", "retriever")

    graph.add_edge("generate", END)
    graph.add_edge("general_llm", END)

    graph.add_edge("web_search", "generate_from_search")
    graph.add_edge("generate_from_search", END)

    return graph.compile()


# Compiled once, reused across requests.
adaptive_rag_app = build_graph()


def run_query(question: str) -> dict:
    """Convenience entrypoint used by the FastAPI layer."""
    initial_state: GraphState = {
        "question": question,
        "original_question": question,
        "rewrite_count": 0,
    }
    final_state = adaptive_rag_app.invoke(initial_state)
    return {
        "answer": final_state.get("answer", ""),
        "route": final_state.get("route", ""),
        "sources": final_state.get("sources", []),
        "rewrite_count": final_state.get("rewrite_count", 0),
    }

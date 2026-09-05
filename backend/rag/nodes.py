"""
LangGraph node implementations.
Each node: takes GraphState in, returns a partial-state dict to merge.
Prompts are loaded from prompts.yaml (not hardcoded) so wording can be tuned
without touching code.
"""
import os
import yaml

from langchain_core.messages import HumanMessage, SystemMessage

from backend.rag.llm_providers import get_llm
from backend.rag.vectorstore import get_retriever
from backend.rag.state import GraphState

_PROMPTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts.yaml")

MAX_REWRITES = 2  # safety cap so the self-correcting loop can't run forever


def _load_prompts() -> dict:
    with open(_PROMPTS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_PROMPTS = _load_prompts()


def _ask(prompt_key: str, **fmt) -> str:
    """Run one LLM call using the system/human templates from prompts.yaml."""
    spec = _PROMPTS[prompt_key]
    llm = get_llm()
    messages = [
        SystemMessage(content=spec["system"]),
        HumanMessage(content=spec["human"].format(**fmt)),
    ]
    response = llm.invoke(messages)
    return response.content.strip()


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def query_analysis(state: GraphState) -> dict:
    """Classify the question into index / general / search."""
    question = state["question"]
    raw = _ask("query_analysis", question=question).lower()

    route = "general"
    if "index" in raw:
        route = "index"
    elif "search" in raw:
        route = "search"
    elif "general" in raw:
        route = "general"

    return {
        "route": route,
        "original_question": state.get("original_question", question),
        "rewrite_count": 0,
    }


def retriever_node(state: GraphState) -> dict:
    """Pull top-k semantically similar chunks from the vector store."""
    retriever = get_retriever()
    docs = retriever.invoke(state["question"])
    return {
        "documents": [d.page_content for d in docs],
        "sources": list({d.metadata.get("source", "unknown") for d in docs}),
    }


def grade(state: GraphState) -> dict:
    """LLM-based relevance check: do the retrieved chunks actually help?"""
    docs = state.get("documents", [])
    if not docs:
        return {"relevant": False}

    combined = "\n\n---\n\n".join(docs)
    verdict = _ask("grade", question=state["question"], document=combined).lower()
    return {"relevant": verdict.startswith("y")}


def rewrite(state: GraphState) -> dict:
    """Rewrite the query for a better retrieval attempt (self-correcting loop)."""
    count = state.get("rewrite_count", 0) + 1
    new_question = _ask("rewrite", question=state["question"])
    return {"question": new_question, "rewrite_count": count}


def generate(state: GraphState) -> dict:
    """Generate the final answer from retrieved document context."""
    context = "\n\n---\n\n".join(state.get("documents", []))
    answer = _ask("generate", context=context, question=state["original_question"])
    return {"answer": answer}


def general_llm(state: GraphState) -> dict:
    """Answer directly from the LLM's own knowledge, no retrieval."""
    answer = _ask("general_llm", question=state["question"])
    return {"answer": answer, "sources": []}


def web_search_node(state: GraphState) -> dict:
    """Fetch live results from Tavily for real-time questions."""
    from config import settings

    if not settings.tavily_api_key:
        return {
            "web_results": [],
            "documents": [],
            "sources": [],
            "answer": (
                "Web search is not configured (TAVILY_API_KEY missing in .env), "
                "so I can't fetch real-time results for this question."
            ),
        }

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    results = client.search(query=state["question"], max_results=5)
    snippets = [r.get("content", "") for r in results.get("results", [])]
    sources = [r.get("url", "") for r in results.get("results", [])]

    return {"web_results": snippets, "documents": snippets, "sources": sources}


def generate_from_search(state: GraphState) -> dict:
    """Generate the final answer from web search snippets."""
    if state.get("answer"):
        # web_search_node already produced a fallback answer (no API key case)
        return {"answer": state["answer"]}
    context = "\n\n---\n\n".join(state.get("web_results", []))
    answer = _ask("web_search_answer", context=context, question=state["original_question"])
    return {"answer": answer}
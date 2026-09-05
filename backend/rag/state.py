"""
Graph state schema — the shared object that flows through every node.
"""
from typing import List, Optional, TypedDict


class GraphState(TypedDict, total=False):
    question: str                 # current question (may be rewritten mid-flow)
    original_question: str        # question as first asked by the user
    route: str                    # "index" | "general" | "search"
    documents: List[str]          # retrieved chunk texts
    web_results: List[str]        # web search snippets
    relevant: bool                # grade node output
    rewrite_count: int            # guards against infinite rewrite loops
    answer: str                   # final answer
    sources: List[str]            # source names/urls used for the answer

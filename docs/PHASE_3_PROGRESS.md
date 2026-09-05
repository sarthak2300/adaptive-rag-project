# Phase 3 — LangGraph Agent (the core of the project)

## What was built

### 1. `backend/rag/state.py`
`GraphState` (TypedDict) — the shared object flowing through every node:
`question`, `original_question`, `route`, `documents`, `web_results`,
`relevant`, `rewrite_count`, `answer`, `sources`.

### 2. `backend/rag/nodes.py` — all 7 nodes from your flow diagram
| Node | What it does |
|---|---|
| `query_analysis` | LLM classifies question → `index` / `general` / `search` |
| `retriever_node` | Pulls top-k chunks from FAISS/Qdrant via `get_retriever()` |
| `grade` | LLM checks if retrieved chunks actually answer the question |
| `rewrite` | Rewrites the query for a better retry (capped at `MAX_REWRITES = 2` so the loop can't run forever) |
| `generate` | Final answer from document context |
| `general_llm` | Direct answer, no retrieval |
| `web_search_node` | Tavily live search (gracefully degrades with a clear message if `TAVILY_API_KEY` is missing, instead of crashing) |
| `generate_from_search` | Final answer from web snippets |

All prompts are pulled from `prompts.yaml` via a small `_ask()` helper — no
hardcoded prompt text in the node logic itself.

### 3. `backend/rag/graph.py`
Wires it into an actual `StateGraph`, matching your diagram exactly:

```
START -> query_analysis
   ├── index   -> retriever -> grade -> (relevant ? generate : rewrite -> retriever)  [loop]
   ├── general -> general_llm -> END
   └── search  -> web_search -> generate_from_search -> END
```

- `route_after_analysis` / `route_after_grade` are the conditional-edge
  functions.
- **Safety valve**: if `rewrite_count` hits `MAX_REWRITES` (2) without the
  grader ever saying "relevant", it still routes to `generate` instead of
  looping infinitely — answers with best-effort context rather than hanging.
- `run_query(question)` — single entrypoint the FastAPI layer will call;
  compiles the graph once at import time and reuses it per request.

## Checks performed
| File | `py_compile` | Notes |
|---|---|---|
| `backend/rag/state.py` | ✅ Pass | |
| `backend/rag/nodes.py` | ✅ Pass | |
| `backend/rag/graph.py` | ✅ Pass | |
| `prompts.yaml` path resolution from `nodes.py` | ✅ Pass | Manually resolved the relative path logic and confirmed it points at the real `prompts.yaml` |

Still can't run the actual graph invocation here (needs `langgraph` installed
+ a live LLM key) — logic was traced by hand against the diagram in your
notes and matches node-for-node.

## Interview line this maps to
This is exactly the part your own notes flagged as most important:
> "Ye ek self-correcting retrieval loop hai — agar pehli baar retrieval
> accha nahi hota, to system khud query ko rewrite karke phir try karta hai."
That loop is `grade → rewrite → retriever → grade → ...`, capped by
`MAX_REWRITES` so it's self-correcting but not infinite.

## Next: Phase 4
FastAPI backend (`/rag/query`, `/rag/documents/upload` endpoints), MongoDB
chat history (Motor async), and the Streamlit frontend (login + chat + file
upload).

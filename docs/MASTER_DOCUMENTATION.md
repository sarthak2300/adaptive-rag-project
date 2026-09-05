# Adaptive RAG Chatbot — Master Documentation

This is the complete, final write-up for the project — how it's built, how
every piece works together, and how to run it. Built to match your original
"Adaptive RAG Project — Explanation Guide" section-by-section, so your
existing interview notes describe this exact codebase.

---

## 1. What this project is

An **agentic RAG chatbot** that, for every question, decides for itself
where the answer should come from:
1. **Your uploaded documents** (`index` route)
2. **The LLM's own general knowledge** (`general` route)
3. **Live web search** (`search` route)

This is different from a normal RAG bot, which always retrieves from
documents even when the answer isn't there — this one routes intelligently,
and if a retrieval attempt comes back irrelevant, it **rewrites the query
and tries again** before giving up (the "self-correcting loop").

---

## 2. High-level architecture

```
Streamlit UI  →  FastAPI Backend  →  LangGraph Agent  →  Response
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ↓                      ↓                      ↓
              Retriever                General LLM            Web Search
            (FAISS / Qdrant)          (OpenAI/Groq/Gemini)      (Tavily)
                    ↓
          Chat History (MongoDB) ← every user + assistant message saved
```

Three layers, same as your notes:
- **UI Layer** — `frontend/app.py` (Streamlit: login, chat, upload)
- **API Layer** — `backend/main.py` (FastAPI: `/rag/query`, `/rag/documents/upload`)
- **Orchestration Layer** — `backend/rag/graph.py` (the LangGraph agent)

---

## 3. The LangGraph flow (the core of the project)

```
START
  ↓
query_analysis  (LLM classifies: index / general / search)
  ↓
  ├── index  → retriever → grade (relevant?)
  │                          ├── NO  → rewrite → retriever   (loops, max 2x)
  │                          └── YES → generate → END
  ├── general → general_llm → END
  └── search  → web_search → generate_from_search → END
```

### Node-by-node, what each one does and which file it lives in

| Node | File | Role |
|---|---|---|
| `query_analysis` | `backend/rag/nodes.py` | Asks the LLM to classify the question into `index`/`general`/`search` using the prompt in `prompts.yaml` |
| `retriever_node` | `backend/rag/nodes.py` → `backend/rag/vectorstore.py` | Pulls the top-k semantically similar chunks from FAISS/Qdrant |
| `grade` | `backend/rag/nodes.py` | A second LLM call checks: do these chunks actually contain the answer? Because vector similarity ≠ actual relevance |
| `rewrite` | `backend/rag/nodes.py` | If not relevant, LLM rewrites the question for a better retrieval attempt. Capped at `MAX_REWRITES = 2` so it can't loop forever |
| `generate` | `backend/rag/nodes.py` | Builds the final answer from the retrieved document context |
| `general_llm` | `backend/rag/nodes.py` | Answers directly from the model's own knowledge, no retrieval |
| `web_search_node` | `backend/rag/nodes.py` | Calls Tavily for live results; degrades gracefully with a clear message if `TAVILY_API_KEY` isn't set (never crashes) |
| `generate_from_search` | `backend/rag/nodes.py` | Builds the final answer from web search snippets |

The graph itself (nodes + conditional edges + the loop) is wired in
`backend/rag/graph.py`, using `route_after_analysis()` and
`route_after_grade()` as the conditional-edge functions.

**How to explain this in an interview** (from your own notes, still accurate):
> "Ye ek self-correcting retrieval loop hai — agar pehli baar retrieval
> accha nahi hota, to system khud query ko rewrite karke phir try karta hai,
> jo traditional static RAG se better hai."

---

## 4. Document ingestion pipeline

```
User uploads PDF/TXT/MD
   ↓
Load  (PyPDFLoader for .pdf, TextLoader for .txt/.md)          — backend/rag/ingestion.py
   ↓
Chunk (RecursiveCharacterTextSplitter, size=1000, overlap=150) — backend/rag/ingestion.py
   ↓
Embed (HuggingFace Sentence Transformers, local & free)        — backend/rag/llm_providers.py
   ↓
Store (FAISS local index, or Qdrant if VECTOR_STORE=qdrant)    — backend/rag/vectorstore.py
   ↓
Ready for retrieval
```

**Why `chunk_overlap=150`?** So context isn't lost when important info sits
right at a chunk boundary — the overlap keeps continuity between adjacent
chunks (this was in your original notes and is preserved exactly).

**Why local embeddings instead of OpenAI embeddings?** Free, no API cost,
runs offline once the model is downloaded once.

---

## 5. Tech stack and why each piece was chosen

| Component | Technology | Why |
|---|---|---|
| Orchestration | **LangGraph** | Graph-based state machine — clean way to handle conditional branching and loops (the rewrite loop) vs. messy if/else chains |
| Backend API | **FastAPI** | Async, auto-generated Swagger docs at `/docs`, fast |
| Vector DB | **FAISS** (dev) / **Qdrant** (prod) | FAISS is free and local for development; Qdrant is the scalable, persistent option for production — switch with one env var |
| Embeddings | **HuggingFace Sentence Transformers** | Free, local, avoids per-call embedding API cost |
| LLM Providers | **OpenAI / Groq / Gemini** | Multi-provider flexibility — swap for cost or speed via `LLM_PROVIDER` in `.env` |
| Chat Memory | **MongoDB** (via Motor, async) | Persistent, session-based chat history |
| Web Search | **Tavily** | LLM-optimized search API, returns clean, citation-friendly results |
| Frontend | **Streamlit** | Fast to build, has chat UI + file upload primitives built in |

---

## 6. API reference

| Method | Path | Request body | Response |
|---|---|---|---|
| `POST` | `/rag/query` | `{"question": str, "session_id": str}` | `{"answer", "route", "sources", "rewrite_count"}` |
| `POST` | `/rag/documents/upload` | multipart file (`.pdf`/`.txt`/`.md`) | `{"file", "pages_loaded", "chunks_created", "chunks_stored", ...}` |
| `GET` | `/rag/history/{session_id}` | — | `{"session_id", "messages": [...]}` |
| `GET` | `/health` | — | `{"status": "ok"}` |

Interactive docs auto-generated by FastAPI at `http://localhost:8000/docs`
once the backend is running.

---

## 7. Full file map

```
adaptive_rag/
├── README.md                 # setup + run instructions
├── requirements.txt          # all dependencies
├── .env.example               # every configurable value, copy to .env
├── config.py                  # single Settings object (pydantic-settings)
├── prompts.yaml                # all 6 LLM prompts used by the graph nodes
│
├── backend/
│   ├── main.py                 # FastAPI app: /rag/query, /rag/documents/upload, /rag/history
│   ├── schemas.py               # Pydantic request/response models
│   ├── db/
│   │   └── mongo.py              # async chat history (Motor)
│   └── rag/
│       ├── llm_providers.py      # get_llm() factory (OpenAI/Groq/Gemini) + get_embeddings()
│       ├── vectorstore.py         # FAISS/Qdrant abstraction, add_documents(), get_retriever()
│       ├── ingestion.py            # load -> chunk -> embed -> store pipeline
│       ├── state.py                 # GraphState TypedDict
│       ├── nodes.py                  # all 7 LangGraph node functions
│       └── graph.py                   # StateGraph wiring, conditional edges, run_query()
│
├── frontend/
│   └── app.py                  # Streamlit UI: login, sidebar upload, chat with route badges
│
└── docs/
    ├── PHASE_1_PROGRESS.md      # scaffold + config + prompts
    ├── PHASE_2_PROGRESS.md      # LLM providers + vector store + ingestion
    ├── PHASE_3_PROGRESS.md      # LangGraph agent
    ├── PHASE_4_PROGRESS.md      # FastAPI + MongoDB + Streamlit
    └── MASTER_DOCUMENTATION.md  # this file
```

---

## 8. How to run it

```bash
cd adaptive_rag
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: add at least one LLM key (OPENAI_API_KEY/GROQ_API_KEY/GOOGLE_API_KEY),
# set MONGO_URI to a running MongoDB instance, optionally add TAVILY_API_KEY
```

Terminal 1:
```bash
uvicorn backend.main:app --reload --port 8000
```

Terminal 2:
```bash
streamlit run frontend/app.py
```

Then: open the Streamlit URL → log in with any username → upload a PDF →
ask a document question, a general-knowledge question, and a current-events
question, and watch the route badge change (📄 / 🧠 / 🌐) for each.

---

## 9. Known limitations (unchanged from your original notes, still honest)

1. Vector store is one shared collection — no per-user/per-session
   isolation yet.
2. No document-deletion endpoint yet.
3. FAISS now persists to disk (fixed vs. earlier in-memory-only version),
   but Qdrant remains the better choice for concurrent, multi-process
   production use.
4. Chat history (MongoDB) and the vector store are separate systems — they
   aren't transactionally in sync if one fails mid-operation.

Mentioning these unprompted in an interview reads as maturity, not weakness
— exactly as your original notes point out.

---

## 10. A note on how this was actually built

This sandbox environment has **no internet access**, so every file here was
written and validated with `python -m py_compile` (syntax-level check) and,
where possible, by hand-tracing the logic against your architecture diagram
— but the actual libraries (FastAPI, LangGraph, LangChain, FAISS, Motor,
Streamlit, Tavily) were never installed or executed here. You'll get the
real, live run the first time you do `pip install -r requirements.txt` and
start the two servers on your own machine. If anything errors on first run,
it's most likely a missing `.env` value or a package version mismatch —
paste me the traceback and I'll fix it.

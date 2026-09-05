# Phase 4 — FastAPI Backend, MongoDB, Streamlit Frontend (final phase)

## What was built

### 1. `backend/db/mongo.py`
Async MongoDB (Motor) chat history: `save_message()`, `get_history()`,
`list_sessions()`. Every user question and assistant answer is stored per
`session_id`, with `route` + `sources` saved in `meta` so the UI can show
which path (index/general/search) answered each turn.

### 2. `backend/schemas.py`
Pydantic request/response models: `QueryRequest`, `QueryResponse`,
`UploadResponse`, `HistoryResponse`.

### 3. `backend/main.py` — the API Layer
| Endpoint | Behavior |
|---|---|
| `POST /rag/query` | Saves user msg → runs `run_query()` (the LangGraph agent) → saves assistant msg → returns answer + route + sources |
| `POST /rag/documents/upload` | Validates extension, writes to a temp file, calls `ingest_file()`, cleans up temp file, returns ingestion stats |
| `GET /rag/history/{session_id}` | Returns full chat history for a session |
| `GET /health` | Liveness check |
- CORS enabled (open) so the Streamlit frontend can call it from a different
  port without extra config.
- LLM/config errors are caught and returned as HTTP 500 with the real error
  message instead of crashing silently — important for debugging in a demo.

### 4. `frontend/app.py` — the UI Layer
- Simple username-based "login" (session_id) — no separate auth backend
  needed for a college-project demo.
- Sidebar: file uploader (PDF/TXT/MD) → calls `/rag/documents/upload`,
  shows chunk/page stats on success.
- Main chat: `st.chat_input`, history loaded from Mongo on first load,
  each assistant reply shows a **route badge** (📄 Document / 🧠 General /
  🌐 Web search) — this is exactly what your demo script (section 10) asks
  you to show live.
- Sources shown in a collapsible expander when available.

### 5. `README.md`
Full setup + run instructions (venv, `.env`, two terminals: `uvicorn` +
`streamlit run`), project layout tree, endpoint table.

## Checks performed
| File | `py_compile` | Notes |
|---|---|---|
| `backend/db/mongo.py` | ✅ Pass | |
| `backend/schemas.py` | ✅ Pass | |
| `backend/main.py` | ✅ Pass | |
| `frontend/app.py` | ✅ Pass | |

## 🎉 Project status: complete
All 4 phases done. Every module from your original architecture diagram
exists and is wired together:
```
Streamlit UI → FastAPI Backend → LangGraph Agent → Response
                                       ↓
                 Retriever(FAISS/Qdrant) | General LLM | Web Search(Tavily)
                                       ↓
                            Chat History (MongoDB)
```

## What YOU need to do to actually run it (since I have no internet here)
1. `pip install -r requirements.txt`
2. `cp .env.example .env` and fill in at least one LLM key + Mongo URI
   (Tavily key optional but needed for the `search` route to work fully)
3. Start MongoDB locally (or use Atlas URI)
4. `uvicorn backend.main:app --reload --port 8000`
5. In a second terminal: `streamlit run frontend/app.py`
6. Test all 3 routes exactly like your demo script section 10:
   - Upload a PDF → ask a document-specific question (→ `index` route)
   - Ask "What is Python?" (→ `general` route)
   - Ask "today's news" (→ `search` route, needs Tavily key)

## Known rough edges to mention honestly if asked (matches your own notes)
- FAISS now persists to disk between restarts (fixed vs. your original
  limitation #1), but it's still not as scalable as Qdrant for concurrent
  writes — Qdrant remains the recommended prod path.
- Still one shared vector collection (no per-user isolation) — noted as a
  roadmap item, same as your original doc.
- No document-deletion endpoint yet — same as your original doc.

Everything above was built to match your `Adaptive RAG Project — Explanation
Guide` document section-by-section, so your existing interview notes
(sections 5, 6, 9) describe this exact codebase accurately.

# Phase 2 — LLM Providers, Vector Store, Document Ingestion

## What was built

### 1. `backend/rag/llm_providers.py`
- `get_llm(temperature)` — factory that returns a LangChain chat model for
  **OpenAI / Groq / Gemini**, chosen purely by `LLM_PROVIDER` in `.env`.
  Raises a clear error if the matching API key is missing.
- `get_embeddings()` — local HuggingFace Sentence-Transformers embeddings
  (free, no API cost, matches your doc's reasoning for choosing them).

### 2. `backend/rag/vectorstore.py`
- `get_vectorstore()` — cached singleton, backed by **FAISS** (dev, in-memory
  + local disk persistence via `save_local`/`load_local`) or **Qdrant** (prod,
  via `VECTOR_STORE=qdrant` in `.env`). Switching backend = one env var, zero
  code changes elsewhere.
- `add_documents(chunks)` — embeds + stores chunks; auto-persists FAISS to disk
  after every add (this directly addresses limitation #1 from your notes —
  FAISS is still in-memory per process, but now survives restarts because it's
  reloaded from `FAISS_INDEX_PATH` on next boot).
- `get_retriever(k)` — returns a retriever with `top_k` from settings.

### 3. `backend/rag/ingestion.py`
- `ingest_file(file_path, source_name)` — full pipeline: load (PyPDFLoader for
  `.pdf`, TextLoader for `.txt`/`.md`) → chunk
  (`RecursiveCharacterTextSplitter`, size=1000, overlap=150) → embed → store.
- Returns a status dict (`pages_loaded`, `chunks_created`, `chunks_stored`)
  so the API layer can report ingestion results back to the UI.
- `chunk_overlap=150` kept exactly as your notes explain: prevents important
  info from being lost across a chunk boundary.

### 4. Package files
- `backend/__init__.py`, `backend/rag/__init__.py`, `backend/db/__init__.py`
  added so everything imports cleanly as a package.

## Checks performed
| File | `py_compile` | Notes |
|---|---|---|
| `backend/rag/llm_providers.py` | ✅ Pass | |
| `backend/rag/vectorstore.py` | ✅ Pass | |
| `backend/rag/ingestion.py` | ✅ Pass | |

As before: syntax/logic verified here; real end-to-end run (actually
embedding text, hitting OpenAI, writing FAISS to disk) needs your machine
with internet + `pip install -r requirements.txt` + a filled `.env`.

## Design decisions worth knowing (for your interview/demo notes too)
- Vector store is a **singleton per process** — avoids reloading FAISS from
  disk on every request.
- FAISS bootstrap trick: creates a store with one dummy doc then deletes it,
  so `get_retriever()` never breaks even before any file is uploaded.
- Qdrant path auto-creates the collection (384 dims for MiniLM-L6-v2) if it
  doesn't exist yet — no manual setup step needed.

## Next: Phase 3
Build the LangGraph agent itself:
`backend/rag/state.py` (graph state schema), `backend/rag/nodes.py`
(`query_analysis`, `retriever`, `grade`, `rewrite`, `generate`, `web_search`,
`general_llm`), and `backend/rag/graph.py` (wiring the conditional edges +
the self-correcting rewrite loop).

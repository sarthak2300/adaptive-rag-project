# Adaptive RAG Chatbot

Agentic RAG chatbot that routes each question to the best source — your
uploaded documents, the LLM's general knowledge, or live web search — using
a LangGraph agent with a self-correcting retrieval loop.

## Setup

```bash
cd adaptive_rag
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env: add OPENAI_API_KEY (or GROQ/GEMINI), TAVILY_API_KEY,
# and make sure MongoDB is running (MONGO_URI)
```

You need, at minimum:
- One LLM provider key (OpenAI / Groq / Gemini) matching `LLM_PROVIDER`
- A running MongoDB instance (local `mongod` or Atlas URI) for chat history
- A Tavily API key for the `search` route (optional — app degrades
  gracefully with a clear message if missing)

## Run

Terminal 1 — backend:
```bash
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 — frontend:
```bash
streamlit run frontend/app.py
```

Then open the Streamlit URL, "log in" with any username, upload a PDF/TXT,
and start chatting.

## Project layout

```
adaptive_rag/
├── config.py                # single Settings object, reads .env
├── prompts.yaml             # all LLM prompts used by graph nodes
├── requirements.txt
├── .env.example
├── backend/
│   ├── main.py               # FastAPI app + endpoints
│   ├── schemas.py            # request/response models
│   ├── db/
│   │   └── mongo.py          # async chat history (Motor)
│   └── rag/
│       ├── llm_providers.py  # OpenAI/Groq/Gemini + embeddings factory
│       ├── vectorstore.py    # FAISS/Qdrant abstraction
│       ├── ingestion.py      # load -> chunk -> embed -> store
│       ├── state.py          # LangGraph state schema
│       ├── nodes.py          # query_analysis, retriever, grade, rewrite, generate...
│       └── graph.py          # graph wiring + conditional edges + rewrite loop
├── frontend/
│   └── app.py                # Streamlit UI (login, chat, upload)
└── docs/
    ├── PHASE_1_PROGRESS.md
    ├── PHASE_2_PROGRESS.md
    ├── PHASE_3_PROGRESS.md
    └── PHASE_4_PROGRESS.md
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/rag/query` | Ask a question — runs the LangGraph agent |
| POST | `/rag/documents/upload` | Upload a PDF/TXT to ingest into the vector store |
| GET | `/rag/history/{session_id}` | Get chat history for a session |
| GET | `/health` | Liveness check |

## Known limitations (see `docs/PHASE_2_PROGRESS.md` for detail)
- FAISS persists to disk now, but Qdrant is still the better choice for
  true multi-process / production deployments.
- No per-user document collections yet — one shared vector store.
- No document-deletion endpoint yet.

# Phase 1 — Project Scaffold, Config, Prompts

## What was built
- `adaptive_rag/` project folder structure:
  - `backend/rag/`, `backend/db/`, `frontend/`, `docs/`, `data/uploads/`
- `requirements.txt` — all dependencies (FastAPI, LangGraph, LangChain, FAISS,
  Qdrant client, sentence-transformers, Tavily, Motor/PyMongo, Streamlit).
- `.env.example` — every configurable value (API keys, model names, chunk size,
  Mongo URI, vector store choice) with sane defaults.
- `config.py` — single `Settings` object (pydantic-settings) that every module
  will import, instead of scattered `os.getenv()` calls.
- `prompts.yaml` — all 6 prompts the graph nodes will use: `query_analysis`,
  `grade`, `rewrite`, `generate`, `general_llm`, `web_search_answer`.

## Checks performed
| Check | Result |
|---|---|
| `prompts.yaml` parses with `yaml.safe_load` | ✅ Pass — 6 top-level keys found |
| `config.py` compiles (`py_compile`) | ✅ Pass — no syntax errors |
| Directory structure created | ✅ Pass |

## ⚠️ Environment limitation (important, read this)
This sandbox has **no internet access**, so I cannot `pip install` FastAPI,
LangGraph, LangChain, etc. here to run live/integration tests. What I *can* do
here:
- Validate Python syntax (`py_compile`) on every file
- Validate YAML/JSON structure
- Logic-check the code by reading it carefully

What I **can't** do here: actually start the FastAPI server, run the LangGraph
graph, hit OpenAI/Tavily APIs, or connect to MongoDB. You'll do the real run:
```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your API keys
```
I'll flag this once and keep going — no need to repeat it every phase.

## Next: Phase 2
Build `backend/rag/llm_providers.py` (multi-provider LLM factory),
`backend/rag/vectorstore.py` (FAISS/Qdrant), and `backend/rag/ingestion.py`
(load → chunk → embed → store).

"""
FastAPI backend — the "API Layer" from your architecture diagram.

Main endpoints:
  POST   /rag/query              -> runs the LangGraph agent, saves to Mongo
  POST   /rag/documents/upload   -> ingest a PDF/TXT into the vector store
  DELETE /rag/documents          -> clear all stored documents (fresh start)
  GET    /rag/history/{session_id} -> chat history for a session
  GET    /health                 -> simple liveness check
"""
import os
import shutil
import tempfile
import traceback

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.db.mongo import get_history, save_message
from backend.rag.graph import run_query
from backend.rag.ingestion import SUPPORTED_EXTENSIONS, ingest_file
from backend.rag.vectorstore import clear_documents
from backend.schemas import (
    ClearDocumentsResponse,
    HistoryResponse,
    QueryRequest,
    QueryResponse,
    UploadResponse,
)

app = FastAPI(title="Adaptive RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/rag/query", response_model=QueryResponse)
async def rag_query(payload: QueryRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")

    await save_message(payload.session_id, "user", payload.question)

    try:
        result = run_query(payload.question)
    except Exception as exc:  # surfaces LLM/config errors clearly to the UI
        traceback.print_exc()  # full traceback printed to the uvicorn terminal
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await save_message(
        payload.session_id,
        "assistant",
        result["answer"],
        meta={"route": result["route"], "sources": result["sources"]},
    )

    return QueryResponse(**result)


@app.post("/rag/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = ingest_file(tmp_path, source_name=file.filename)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        os.remove(tmp_path)

    return UploadResponse(**result)


@app.delete("/rag/documents", response_model=ClearDocumentsResponse)
async def delete_documents():
    """Wipe the vector store so old uploads stop showing up in new answers."""
    try:
        clear_documents()
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ClearDocumentsResponse(
        status="ok", message="All stored documents were cleared."
    )


@app.get("/rag/history/{session_id}", response_model=HistoryResponse)
async def chat_history(session_id: str):
    messages = await get_history(session_id)
    return HistoryResponse(session_id=session_id, messages=messages)

"""
Document ingestion pipeline:
  load file (PDF / TXT) -> chunk (RecursiveCharacterTextSplitter)
  -> embed (Sentence Transformers) -> store (FAISS / Qdrant)

chunk_size=1000, chunk_overlap=150 by default (see .env / config.py) so
important info that spans a chunk boundary isn't lost — the overlap keeps
continuity between adjacent chunks.
"""
import os
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from backend.rag.vectorstore import add_documents

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def _load_file(file_path: str) -> List[Document]:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader

        return PyPDFLoader(file_path).load()

    if ext in (".txt", ".md"):
        from langchain_community.document_loaders import TextLoader

        return TextLoader(file_path, encoding="utf-8").load()

    raise ValueError(
        f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
    )


def chunk_documents(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


def ingest_file(file_path: str, source_name: str | None = None) -> dict:
    """Full pipeline for one file. Returns a small status report."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    raw_docs = _load_file(file_path)
    for d in raw_docs:
        d.metadata["source"] = source_name or os.path.basename(file_path)

    chunks = chunk_documents(raw_docs)
    stored_count = add_documents(chunks)

    return {
        "file": source_name or os.path.basename(file_path),
        "pages_loaded": len(raw_docs),
        "chunks_created": len(chunks),
        "chunks_stored": stored_count,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }

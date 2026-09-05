"""
Vector store abstraction. Supports FAISS (local, dev) and Qdrant (prod-ready).
Switch via VECTOR_STORE=faiss|qdrant in .env — no other code changes needed.
"""
import os
from typing import List

from langchain_core.documents import Document

from config import settings
from backend.rag.llm_providers import get_embeddings

_vectorstore_singleton = None  # cached instance for the process lifetime


def _load_or_create_faiss():
    from langchain_community.vectorstores import FAISS

    embeddings = get_embeddings()
    index_path = settings.faiss_index_path

    if os.path.exists(index_path):
        return FAISS.load_local(
            index_path, embeddings, allow_dangerous_deserialization=True
        )

    # Bootstrap an empty index with a single throwaway doc, then clear it,
    # so callers always get a usable FAISS object even before any upload.
    dummy = [Document(page_content="init", metadata={"bootstrap": True})]
    store = FAISS.from_documents(dummy, embeddings)
    store.delete([store.index_to_docstore_id[0]])
    return store


def _load_or_create_qdrant():
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams

    embeddings = get_embeddings()
    client = QdrantClient(url=settings.qdrant_url)

    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in existing:
        # all-MiniLM-L6-v2 => 384 dims; adjust if you change embedding model
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=embeddings,
    )


def get_vectorstore():
    """Return a cached vector store instance (FAISS or Qdrant per settings)."""
    global _vectorstore_singleton
    if _vectorstore_singleton is not None:
        return _vectorstore_singleton

    if settings.vector_store.lower() == "qdrant":
        _vectorstore_singleton = _load_or_create_qdrant()
    else:
        _vectorstore_singleton = _load_or_create_faiss()
    return _vectorstore_singleton


def add_documents(chunks: List[Document]) -> int:
    """Embed + store chunks. Persists FAISS to disk after every add."""
    store = get_vectorstore()
    store.add_documents(chunks)

    if settings.vector_store.lower() == "faiss":
        os.makedirs(os.path.dirname(settings.faiss_index_path) or ".", exist_ok=True)
        store.save_local(settings.faiss_index_path)

    return len(chunks)


def get_retriever(k: int | None = None):
    store = get_vectorstore()
    return store.as_retriever(search_kwargs={"k": k or settings.retriever_top_k})


def clear_documents() -> None:
    """Wipe all stored documents so a fresh upload starts from an empty index.

    FAISS: deletes the on-disk index folder and resets the cached singleton.
    Qdrant: deletes and recreates the collection.
    This is what fixes "old PDF keeps showing up after uploading a new one" —
    previously every upload just added MORE chunks to the same shared store,
    so old documents never went away on their own.
    """
    global _vectorstore_singleton

    if settings.vector_store.lower() == "qdrant":
        from qdrant_client import QdrantClient

        client = QdrantClient(url=settings.qdrant_url)
        if client.collection_exists(settings.qdrant_collection):
            client.delete_collection(settings.qdrant_collection)
    else:
        import shutil

        if os.path.exists(settings.faiss_index_path):
            shutil.rmtree(settings.faiss_index_path)

    _vectorstore_singleton = None  # force a fresh, empty store on next use

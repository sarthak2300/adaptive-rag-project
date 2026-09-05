"""
Centralized configuration for the Adaptive RAG project.
Reads from .env (via pydantic-settings) so every module (backend, frontend,
ingestion, graph) pulls settings from ONE place instead of scattered os.getenv calls.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "openai"           # openai | groq | gemini
    openai_api_key: str = ""
    groq_api_key: str = ""
    google_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "llama-3.1-70b-versatile"
    gemini_model: str = "gemini-1.5-flash"

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Vector store
    vector_store: str = "faiss"            # faiss | qdrant
    faiss_index_path: str = "./data/faiss_index"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "adaptive_rag_docs"

    # Web search
    tavily_api_key: str = ""

    # Mongo
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "adaptive_rag"
    mongo_chat_collection: str = "chat_history"

    # Chunking / retrieval
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retriever_top_k: int = 4

    # Misc
    backend_url: str = "http://localhost:8000"


settings = Settings()

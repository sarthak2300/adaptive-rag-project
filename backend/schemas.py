from typing import List, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


class QueryResponse(BaseModel):
    answer: str
    route: str
    sources: List[str] = []
    rewrite_count: int = 0


class UploadResponse(BaseModel):
    file: str
    pages_loaded: int
    chunks_created: int
    chunks_stored: int
    chunk_size: int
    chunk_overlap: int


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[dict]


class ClearDocumentsResponse(BaseModel):
    status: str
    message: str

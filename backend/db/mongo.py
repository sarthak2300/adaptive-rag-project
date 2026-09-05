"""
MongoDB chat history — async via Motor.
Every user message + assistant answer is saved per session_id so a session's
conversation persists across page reloads / logins.
"""
from datetime import datetime, timezone
from typing import List

from motor.motor_asyncio import AsyncIOMotorClient

from config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_collection():
    db = get_client()[settings.mongo_db_name]
    return db[settings.mongo_chat_collection]


async def save_message(session_id: str, role: str, content: str, meta: dict | None = None) -> None:
    """role: 'user' or 'assistant'"""
    doc = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "meta": meta or {},
        "timestamp": datetime.now(timezone.utc),
    }
    await get_collection().insert_one(doc)


async def get_history(session_id: str, limit: int = 50) -> List[dict]:
    cursor = (
        get_collection()
        .find({"session_id": session_id}, {"_id": 0})
        .sort("timestamp", 1)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def list_sessions() -> List[str]:
    return await get_collection().distinct("session_id")

from pymongo import AsyncMongoClient

from app.config import cfg
from app.db.mongo_store import init as store_init

_client: AsyncMongoClient | None = None
_db = None


async def connect() -> None:
    """建连 + mongo_store init（schema 需先经 registry.register_all 注册再建索引）"""
    global _client, _db
    if _db is not None:
        return
    _client = AsyncMongoClient(cfg.MONGO_URI, serverSelectionTimeoutMS=5000)
    _db = _client[cfg.MONGO_DB]
    await store_init(_db)


def get_db():
    if _db is None:
        raise RuntimeError('database not connected')
    return _db


async def close() -> None:
    global _client, _db
    if _client is not None:
        await _client.close()
    _client = None
    _db = None

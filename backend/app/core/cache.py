"""
app/core/cache.py
─────────────────
Async Redis cache for RAG query responses.
Key = SHA256(query + competitor_filter).
TTL = 24 hours (configurable).
"""

import hashlib
import json
from typing import Any, Optional

import redis.asyncio as aioredis
from loguru import logger

from app.core.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


def _cache_key(query: str, extra: str = "") -> str:
    raw = f"{query}::{extra}"
    return "croma_ci:" + hashlib.sha256(raw.encode()).hexdigest()


async def cache_get(query: str, extra: str = "") -> Optional[Any]:
    try:
        r = await get_redis()
        val = await r.get(_cache_key(query, extra))
        if val:
            logger.debug(f"Cache HIT for query: {query[:60]}...")
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Cache GET failed: {e}")
    return None


async def cache_set(query: str, value: Any, extra: str = "") -> None:
    try:
        r = await get_redis()
        await r.setex(
            _cache_key(query, extra),
            settings.RAG_CACHE_TTL_SECONDS,
            json.dumps(value, default=str),
        )
        logger.debug(f"Cache SET for query: {query[:60]}...")
    except Exception as e:
        logger.warning(f"Cache SET failed: {e}")


async def cache_invalidate_pattern(pattern: str) -> int:
    """Flush all keys matching pattern — call after ingestion."""
    try:
        r = await get_redis()
        keys = await r.keys(f"croma_ci:{pattern}*")
        if keys:
            return await r.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache invalidate failed: {e}")
    return 0

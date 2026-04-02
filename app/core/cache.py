import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

redis_client = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)
# decode_responses=True — Redis возвращает строки а не байты.
# Удобно для JSON данных.


async def get_cache(key: str) -> Any | None:
    value = await redis_client.get(key)
    if value:
        return json.loads(value)
    return None


async def set_cache(key: str, value: Any, ttl: int = 60) -> None:
    await redis_client.setex(
        key,
        ttl,
        json.dumps(value, ensure_ascii=False),
    )
    # setex — set with expiry. Ключ автоматически удалится через ttl секунд.
    # ensure_ascii=False — корректно сохраняем кириллицу.


async def delete_cache(key: str) -> None:
    await redis_client.delete(key)
    # Инвалидация кеша — вызываем когда данные изменились.

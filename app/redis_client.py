import redis.asyncio as redis
from app.config import settings

redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    health_check_interval=30,
)

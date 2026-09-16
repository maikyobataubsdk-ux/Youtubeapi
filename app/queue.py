import asyncio
import hashlib
import json
import time
import uuid

from app.config import settings
from app.redis_client import redis_client

def cache_key(action: str, value: str) -> str:
    digest = hashlib.sha256(value.encode()).hexdigest()
    return f"music:cache:{action}:{digest}"

async def submit(action: str, value: str) -> dict:
    key = cache_key(action, value)
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)

    # De-duplicate identical work.
    lock_key = f"music:lock:{action}:{hashlib.sha256(value.encode()).hexdigest()}"
    owner = str(uuid.uuid4())
    acquired = await redis_client.set(lock_key, owner, ex=settings.max_queue_wait, nx=True)

    if not acquired:
        deadline = time.monotonic() + settings.max_queue_wait
        while time.monotonic() < deadline:
            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)
            await asyncio.sleep(0.1)
        # If the original job disappeared, submit a new one.
        acquired = await redis_client.set(lock_key, owner, ex=settings.max_queue_wait, nx=True)

    job_id = str(uuid.uuid4())
    payload = {
        "id": job_id,
        "action": action,
        "value": value,
        "cache_key": key,
        "created": time.time(),
    }

    await redis_client.rpush(settings.queue_name, json.dumps(payload))

    result_key = f"music:result:{job_id}"
    deadline = time.monotonic() + settings.max_queue_wait

    try:
        while time.monotonic() < deadline:
            result = await redis_client.get(result_key)
            if result:
                data = json.loads(result)
                if data.get("ok"):
                    await redis_client.setex(
                        key,
                        settings.cache_ttl,
                        json.dumps(data),
                    )
                return data
            await asyncio.sleep(0.1)

        return {
            "ok": False,
            "error": "worker_timeout",
            "code": "WORKER_TIMEOUT",
            "job_id": job_id,
        }
    finally:
        if acquired:
            try:
                current = await redis_client.get(lock_key)
                if current == owner:
                    await redis_client.delete(lock_key)
            except Exception:
                pass

import asyncio
import json
import logging
import signal

from app.config import settings
from app.redis_client import redis_client
from app.youtube import extract_reliably, normalize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | music-worker | %(message)s",
)
log = logging.getLogger("music-worker")

async def process(job: dict):
    job_id = job["id"]
    action = job["action"]
    value = job["value"]

    try:
        data = await asyncio.wait_for(
            extract_reliably(value, action),
            timeout=settings.job_timeout,
        )
        result = {"ok": True, **normalize(action, data)}
    except asyncio.TimeoutError:
        result = {
            "ok": False,
            "error": "YouTube request timed out.",
            "code": "YT_TIMEOUT",
        }
    except Exception as exc:
        msg = str(exc)
        lower = msg.lower()

        if "sign in to confirm" in lower or "login_required" in lower:
            code = "YT_AUTH_OR_ANTIBOT"
        elif "403" in lower:
            code = "YT_HTTP_403"
        elif "429" in lower or "too many requests" in lower:
            code = "YT_RATE_LIMIT"
        elif "no direct audio format" in lower:
            code = "NO_AUDIO"
        else:
            code = "YT_EXTRACT_ERROR"

        log.warning("job=%s action=%s error=%s", job_id, action, msg[:500])
        result = {"ok": False, "error": msg, "code": code}

    await redis_client.setex(
        f"music:result:{job_id}",
        settings.result_ttl,
        json.dumps(result),
    )

async def worker_loop(worker_id: int):
    log.info("worker-%s started", worker_id)

    while True:
        try:
            item = await redis_client.blpop(settings.queue_name, timeout=5)
            if not item:
                continue

            _, raw = item
            job = json.loads(raw)
            await process(job)

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("worker-%s loop error: %s", worker_id, exc)
            await asyncio.sleep(1)

async def main():
    tasks = [
        asyncio.create_task(worker_loop(i))
        for i in range(settings.youtube_workers)
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

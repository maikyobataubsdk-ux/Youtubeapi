import os
from dataclasses import dataclass

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

@dataclass(frozen=True)
class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    queue_name: str = os.getenv("QUEUE_NAME", "music_api_jobs")
    result_ttl: int = env_int("RESULT_TTL", 90)
    cache_ttl: int = env_int("CACHE_TTL", 240)
    job_timeout: int = env_int("JOB_TIMEOUT", 45)
    api_workers: int = env_int("API_WORKERS", 2)
    youtube_workers: int = env_int("YOUTUBE_WORKERS", 8)
    max_queue_wait: int = env_int("MAX_QUEUE_WAIT", 50)
    max_search_results: int = env_int("MAX_SEARCH_RESULTS", 10)

settings = Settings()

import asyncio
import os
from typing import Any

import yt_dlp

from app.config import settings

TRANSIENT_MARKERS = (
    "429",
    "too many requests",
    "rate limit",
    "temporarily unavailable",
    "timed out",
    "timeout",
    "connection reset",
    "connection aborted",
    "502",
    "503",
    "504",
)

def _base_options() -> dict[str, Any]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "extractor_retries": 2,
        "concurrent_fragment_downloads": 1,
        "http_chunk_size": 10 * 1024 * 1024,
    }

    cookies = os.getenv("YT_COOKIES", "").strip()
    if cookies and os.path.isfile(cookies):
        opts["cookiefile"] = cookies

    # Only enable an external JS runtime if the operator explicitly
    # configured one. This prevents "deno not found" failures.
    js_runtime = os.getenv("YTDLP_JS_RUNTIME", "").strip()
    if js_runtime in {"deno", "node", "quickjs"}:
        opts["js_runtimes"] = {js_runtime: {}}

    return opts

def _extract(url: str, mode: str) -> dict:
    opts = _base_options()
    if mode == "search":
        opts["extract_flat"] = True
        query = f"ytsearch{settings.max_search_results}:{url}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(query, download=False)

    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in TRANSIENT_MARKERS)

async def extract_reliably(url: str, mode: str) -> dict:
    attempts = [
        ("default", False),
        ("ipv4", True),
    ]

    last_error: Exception | None = None

    for name, use_ipv4 in attempts:
        for retry in range(3):
            try:
                if use_ipv4:
                    old = os.environ.get("MUSIC_API_FORCE_IPV4")
                    os.environ["MUSIC_API_FORCE_IPV4"] = "1"
                    try:
                        return await asyncio.to_thread(_extract_with_ipv4, url, mode)
                    finally:
                        if old is None:
                            os.environ.pop("MUSIC_API_FORCE_IPV4", None)
                        else:
                            os.environ["MUSIC_API_FORCE_IPV4"] = old

                return await asyncio.to_thread(_extract, url, mode)

            except Exception as exc:
                last_error = exc
                if retry < 2 and _is_transient(exc):
                    await asyncio.sleep(1.5 * (retry + 1))
                else:
                    break

    raise RuntimeError(str(last_error or "youtube extraction failed"))

def _extract_with_ipv4(url: str, mode: str) -> dict:
    # Use source_address only for this extraction attempt.
    opts = _base_options()
    opts["source_address"] = "0.0.0.0"
    if mode == "search":
        opts["extract_flat"] = True
        query = f"ytsearch{settings.max_search_results}:{url}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(query, download=False)
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def choose_audio(data: dict) -> dict | None:
    formats = [
        f for f in data.get("formats", [])
        if f.get("url")
        and f.get("acodec") not in (None, "none")
        and f.get("vcodec") in (None, "none")
    ]
    if not formats:
        return None

    formats.sort(
        key=lambda f: (
            f.get("abr") or 0,
            f.get("asr") or 0,
            f.get("filesize") or 0,
        ),
        reverse=True,
    )
    return formats[0]

def normalize(action: str, data: dict) -> dict:
    if action == "search":
        results = []
        for item in data.get("entries") or []:
            if not item:
                continue
            results.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "url": item.get("webpage_url") or item.get("url"),
                "duration": item.get("duration"),
                "thumbnail": item.get("thumbnail"),
                "channel": item.get("channel"),
            })
        return {"results": results}

    result = {
        "id": data.get("id"),
        "title": data.get("title"),
        "duration": data.get("duration"),
        "duration_string": data.get("duration_string"),
        "thumbnail": data.get("thumbnail"),
        "uploader": data.get("uploader"),
        "channel": data.get("channel"),
        "webpage_url": data.get("webpage_url"),
    }

    if action == "stream":
        audio = choose_audio(data)
        if not audio:
            raise RuntimeError("No direct audio format was returned by YouTube.")
        result.update({
            "audio_url": audio.get("url"),
            "mime": audio.get("mime"),
            "ext": audio.get("ext"),
            "abr": audio.get("abr"),
            "format_id": audio.get("format_id"),
        })

    return result

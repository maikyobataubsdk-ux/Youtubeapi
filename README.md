# Telegram Music Resolver API v2

FastAPI + Redis + yt-dlp worker-pool service for Telegram VC music bots.

## Features

- Redis-backed queue
- Duplicate request de-duplication
- Short-lived cache for repeated songs
- Multiple async worker tasks in one process
- Timeout and retry/backoff
- IPv4 retry
- Optional server-side cookies
- Optional external JS runtime
- Clean error codes
- Docker Compose
- Nginx reverse proxy
- Health endpoint

## Important reality

This project reduces transient failures; it cannot guarantee that YouTube will
never return 403, 429, login-required, or anti-bot responses. Those are
upstream controls. The API returns structured errors instead of crashing.

## Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose up -d --build --scale worker=8
```

Check:

```bash
curl http://127.0.0.1:8080/health
curl "http://127.0.0.1:8080/search?q=Arijit%20Singh"
```

## Native Ubuntu install

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg redis-server

mkdir -p /opt/telegram_music_api
cd /opt/telegram_music_api

python3 -m venv venv
source venv/bin/activate
pip install -U -r requirements.txt

cp .env.example .env
```

Start API:

```bash
source /opt/telegram_music_api/venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8080 --workers 2
```

Start worker:

```bash
source /opt/telegram_music_api/venv/bin/activate
python worker.py
```

## Cookies

Cookies are optional. Do NOT put `cookies.txt` in Git.

Example:

```env
YT_COOKIES=/etc/music-api/cookies.txt
```

The code only passes the cookie file to yt-dlp when the configured file exists.

## API

```text
GET /health
GET /search?q=...
GET /info?url=...
GET /stream?url=...
```

## Telegram bot usage

Call `/search` when the user types a search term. Immediately before playing,
call `/stream` to get the current direct media URL. Do not permanently store
the returned direct URL.

## Scaling

The API is stateless. The resolver workload is pushed to Redis.

Example:

```bash
docker compose up -d --build --scale worker=8
```

Each worker process runs several async worker tasks according to
`YOUTUBE_WORKERS`.

For very high concurrency, add more VPS instances and point all of them to a
private Redis instance. Do not expose Redis to the public internet.

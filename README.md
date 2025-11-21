# log-simulator — log training factory

Generates *real-time* different log formats in `logs/`:
- `app` — text levels (DEBUG/INFO/WARN/ERROR), request-id, messages
- `json` — JSON Lines, with metadata and sometimes stacktrace
- `nginx` — access log with 2xx/4xx/5xx statuses and response time
- `db` — PostgreSQL-like messages (deadlock, timeout, duplicate key, etc.)
- `system` — systemd-style (`web.service[123]: ERROR ...`)
- `k8s` — JSON with Kubernetes fields (namespace, pod, container) and statuses

Included:
- **docker-compose** (multiple services, each writes its own format)
- **rotation and compression** `.gz` and/or `.zst` (separate `rotator` service)
- **Makefile** with presets: `top`, `p95`, `5xx`, `bulk`, etc.

## Quick Start

```bash
# 1) Start
docker compose up -d
# Check that files are growing
ls -lah logs/*

# 2) Watch the stream
docker compose logs -f app json nginx db system k8s

# 3) Stop
docker compose down
```

By default, settings are taken from `.env` (created by default).

## Settings (.env)

```ini
RATE=10            # lines per second per service
ERROR_RATIO=0.25   # ratio of "errors" (0..1)
JITTER=0.25        # sleep jitter (percentage of period)
ROTATE_INTERVAL=30 # seconds between rotation checks
ROTATE_MIN_SIZE_MB=5
COMPRESS=both      # gzip|zstd|both
LOG_DIR=./logs
```

## Useful Commands (Makefile)

```bash
make up         # start services
make down       # stop and remove
make logs       # follow all
make rotate     # enable/restart rotator
make clean      # remove logs

make top        # top repeating errors
make p95        # 95th percentile response time (nginx)
make 5xx        # 5xx counter by endpoints

# Generate large files quickly and compress:
make bulk LINES=200000 RATE=5000 FORMAT=all COMPRESS=both
```
Dependencies for analysis scripts: `ripgrep (rg)`, `jq`, `awk`.

# log-simulator — тренировочная фабрика логов

Генерирует *в реальном времени* разные форматы логов в `logs/`:
- `app` — текстовые уровни (DEBUG/INFO/WARN/ERROR), request-id, сообщения
- `json` — JSON Lines, с метаданными и иногда stacktrace
- `nginx` — access-лог со статусами 2xx/4xx/5xx и временем ответа
- `db` — PostgreSQL-подобные сообщения (deadlock, timeout, duplicate key и т.п.)
- `system` — systemd-style (`web.service[123]: ERROR ...`)
- `k8s` — JSON с полями Kubernetes (namespace, pod, container) и статусами

В комплекте:
- **docker-compose** (несколько сервисов, каждый пишет свой формат)
- **ротация и компрессия** `.gz` и/или `.zst` (отдельный сервис `rotator`)
- **Makefile** с пресетами: `top`, `p95`, `5xx`, `bulk` и пр.

## Быстрый старт

```bash
# 1) Запуск
docker compose up -d
# Проверить, что файлы растут
ls -lah logs/*

# 2) Смотреть поток
docker compose logs -f app json nginx db system k8s

# 3) Остановить
docker compose down
```

По умолчанию настройки берутся из `.env` (создан по умолчанию).

## Настройки (.env)

```ini
RATE=10            # строк в секунду на каждый сервис
ERROR_RATIO=0.25   # доля «ошибок» (0..1)
JITTER=0.25        # джиттер сна (процент от периода)
ROTATE_INTERVAL=30 # сек между проверками ротации
ROTATE_MIN_SIZE_MB=5
COMPRESS=both      # gzip|zstd|both
LOG_DIR=./logs
```

## Полезные команды (Makefile)

```bash
make up         # поднять сервисы
make down       # остановить и удалить
make logs       # follow по всем
make rotate     # включить/перезапустить ротатор
make clean      # удалить логи

make top        # топ повторяющихся ошибок
make p95        # 95-й перцентиль времени ответа (nginx)
make 5xx        # счетчик 5xx по эндпоинтам

# Сгенерировать большие файлы быстро и сжать:
make bulk LINES=200000 RATE=5000 FORMAT=all COMPRESS=both
```
Зависимости для анализ-скриптов: `ripgrep (rg)`, `jq`, `awk`.

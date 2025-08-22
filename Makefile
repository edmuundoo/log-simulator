.PHONY: up down logs rotate clean top p95 5xx bulk tail

SHELL := /bin/bash

LINES ?= 200000
RATE ?= 5000
FORMAT ?= all
COMPRESS ?= both

up: ; docker compose up -d --build
down: ; docker compose down -v
logs: ; docker compose logs -f app json nginx db system k8s
rotate: ; docker compose up -d rotator
clean: ; rm -rf logs/* || true

top:
	rg "ERROR" logs/** 2>/dev/null | sed -E 's/[0-9a-f-]{8,}/UUID/g; s/\b[0-9]{3,}\b/NUM/g' | sort | uniq -c | sort -nr | head

p95:
	@awk '{print $$NF}' logs/nginx/access.log | sort -n | awk 'BEGIN{n=0} {a[++n]=$$1} END{if(n==0){print "no data"; exit} idx=int(0.95*n); if(idx<1) idx=1; print a[idx]}'

5xx:
	@awk '$$9 ~ /^5/ {print $$7}' logs/nginx/access.log | sort | uniq -c | sort -nr | head

bulk:
	@if [ "$(FORMAT)" = "all" ]; then \
	  for f in app json nginx db system k8s; do \
	    echo "==> $$f"; \
	    docker compose run --rm cli python /app/log_simulator/generate.py --format $$f --dir /logs --rate $(RATE) --error-ratio 0.3 --lines $(LINES); \
	  done; \
	else \
	  docker compose run --rm cli python /app/log_simulator/generate.py --format $(FORMAT) --dir /logs --rate $(RATE) --error-ratio 0.3 --lines $(LINES); \
	fi; \
	docker compose run --rm cli bash -lc 'COMPRESS=$(COMPRESS) /app/once_compress.sh'

tail:
	tail -f logs/*/*.log

#!/usr/bin/env bash
set -euo pipefail
ROTATE_INTERVAL="${ROTATE_INTERVAL:-30}"
ROTATE_MIN_SIZE_MB="${ROTATE_MIN_SIZE_MB:-5}"
COMPRESS="${COMPRESS:-both}"

compress_file () {
  local f="$1"
  case "$COMPRESS" in
    gzip) gzip -f "$f" ;;
    zstd) zstd -q --rm "$f" ;;
    both) gzip -c "$f" > "$f.gz"; zstd -q -c "$f" > "$f.zst"; rm -f "$f" ;;
    *) echo "Unknown COMPRESS=$COMPRESS for $f" ;;
  esac
}

echo "[rotator] interval=${ROTATE_INTERVAL}s min_size=${ROTATE_MIN_SIZE_MB}MB compress=${COMPRESS}"

while true; do
  for f in /logs/*/*.log; do
    [ -f "$f" ] || continue
    size_bytes=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)
    min_bytes=$(( ROTATE_MIN_SIZE_MB * 1024 * 1024  ))
    if [ "$size_bytes" -ge "$min_bytes" ]; then
      ts=$(date +"%Y%m%d-%H%M%S")
      new="$f.$ts"
      mv "$f" "$new" && : > "$f"
      echo "[rotator] rotated $f -> $new"
      compress_file "$new"
    fi
  done
  sleep "$ROTATE_INTERVAL"
done

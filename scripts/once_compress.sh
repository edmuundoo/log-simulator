#!/usr/bin/env bash
set -euo pipefail
COMPRESS="${COMPRESS:-both}"
compress_file () {
  local f="$1"
  case "$COMPRESS" in
    gzip) gzip -f "$f" ;;
    zstd) zstd -q --rm "$f" ;;
    both) gzip -c "$f" > "$f.gz"; zstd -q -c "$f" > "$f.zst"; rm -f "$f" ;;
    *) echo "Unknown COMPRESS=$COMPRESS" ;;
  esac
}
shopt -s nullglob
for f in /logs/*/*.log; do
  [ -s "$f" ] || continue
  ts=$(date +"%Y%m%d-%H%M%S")
  new="$f.$ts"
  mv "$f" "$new" && : > "$f"
  compress_file "$new"
done
echo "One-time compression done."

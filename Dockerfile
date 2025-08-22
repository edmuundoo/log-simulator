FROM python:3.11-alpine
RUN apk add --no-cache bash coreutils grep sed gawk gzip zstd tzdata
WORKDIR /app
COPY log_simulator/ /app/log_simulator/
COPY scripts/rotator.sh /app/rotator.sh
COPY scripts/once_compress.sh /app/once_compress.sh
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

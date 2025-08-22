#!/usr/bin/env python3
import argparse, os, random, sys, threading, time
from pathlib import Path
from datetime import datetime
from log_simulator import formats

FORMATS = ["app","json","nginx","db","system","k8s"]

def parse_args():
    p = argparse.ArgumentParser(description="log-simulator: многоформатный генератор логов")
    p.add_argument("--dir", default="/logs", help="каталог для логов")
    p.add_argument("--format", choices=FORMATS, help="один формат")
    p.add_argument("--formats", nargs="+", choices=FORMATS, help="несколько форматов сразу")
    p.add_argument("--rate", type=float, default=10.0, help="строк в секунду на генератор")
    p.add_argument("--error-ratio", type=float, default=0.2, help="вероятность ошибки (0..1)")
    p.add_argument("--jitter", type=float, default=0.25, help="временной джиттер сна (доля от периода)")
    p.add_argument("--lines", type=int, default=0, help="если >0 — сгенерировать указанное число строк и выйти")
    p.add_argument("--duration", type=float, default=0.0, help="если >0 — работать N секунд и выйти")
    return p.parse_args()

def writer(path: Path, line_fn, rate: float, error_ratio: float, jitter: float, lines: int, duration: float):
    path.parent.mkdir(parents=True, exist_ok=True)
    period = 1.0 / max(rate, 0.0001)
    end_time = time.time() + duration if duration and duration > 0 else None
    count = 0
    print(f"[{datetime.now().strftime('%H:%M:%S')}] writing -> {path} @ ~{rate}/s")
    with open(path, "a", buffering=1) as f:
        while True:
            f.write(line_fn(error_ratio))
            count += 1
            if lines and count >= lines:
                break
            if end_time and time.time() >= end_time:
                break
            sleep = period * (1.0 + random.uniform(-jitter, jitter))
            if sleep > 0:
                time.sleep(sleep)

def main():
    args = parse_args()
    base = Path(args.dir)
    mapping = {
        "app":     (base / "app" / "app.log",     lambda r: formats.app_line(r)),
        "json":    (base / "json" / "app.jsonl",  lambda r: formats.json_line(r)),
        "nginx":   (base / "nginx" / "access.log",lambda r: formats.nginx_line(r)),
        "db":      (base / "db" / "db.log",       lambda r: formats.db_line(r)),
        "system":  (base / "system" / "sys.log",  lambda r: formats.system_line(r)),
        "k8s":     (base / "k8s" / "pod.log",     lambda r: formats.k8s_line(r)),
    }
    targets = []
    if args.format:
        targets = [args.format]
    elif args.formats:
        targets = args.formats
    else:
        targets = list(mapping.keys())
    threads = []
    for fmt in targets:
        path, fn = mapping[fmt]
        t = threading.Thread(target=writer, args=(path, fn, args.rate, args.error_ratio, args.jitter, args.lines, args.duration), daemon=True)
        t.start()
        threads.append(t)
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nStopping…")

if __name__ == "__main__":
    main()

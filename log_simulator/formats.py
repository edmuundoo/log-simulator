import random, time, json, uuid
from datetime import datetime, timezone

LEVELS = ["DEBUG", "INFO", "WARN", "ERROR"]
HTTP_METHODS = ["GET","POST","PUT","PATCH","DELETE"]
PATHS = ["/api/login","/api/logout","/api/items","/api/items/42","/api/search","/health","/"]
STATUS_GOOD = [200,201,202,204,302]
STATUS_BAD = [400,401,403,404,409,422,429,500,502,503,504]

DB_ERRORS = [
    "ERROR: deadlock detected",
    "ERROR: duplicate key value violates unique constraint",
    "ERROR: could not serialize access due to concurrent update",
    "ERROR: connection timeout",
    "FATAL: terminating connection due to administrator command",
    "ERROR: syntax error at or near \"FROMM\"",
]

EXCEPTIONS = [
    ("ValueError", "invalid literal for int()"),
    ("KeyError", "missing key 'user_id'"),
    ("TimeoutError", "operation timed out"),
    ("AssertionError", "expected status 200, got 500"),
    ("IOError", "failed to read file"),
]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def rand_req_id():
    return f"RID-{uuid.uuid4().hex[:8]}"

def app_line(error_ratio: float):
    rid = rand_req_id()
    lvl = "ERROR" if random.random() < error_ratio else random.choice(LEVELS[:-1])
    msg = random.choice([
        "User logged in",
        "Cache miss",
        "Starting background job",
        "Payment processed",
        "FeatureFlag off: degrade_stats",
        "Retry attempt 2",
        "DB query failed",
        "Upstream 502",
        "Unhandled exception",
    ])
    tb = ""
    if lvl == "ERROR" and random.random() < 0.35:
        tb = "\nTraceback (most recent call last):\n  File \"service.py\", line 42, in handle\n    1/0\nZeroDivisionError: division by zero"
    return f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} {lvl} rid={rid} {msg}{tb}\n"

def json_line(error_ratio: float):
    lvl = "ERROR" if random.random() < error_ratio else random.choice(LEVELS[:-1])
    rid = rand_req_id()
    payload = {
        "ts": now_iso(),
        "level": lvl,
        "rid": rid,
        "msg": random.choice([
            "processing request",
            "authorization failed",
            "db timeout",
            "cache warmup",
            "render finished",
            "queue publish",
            "exception thrown",
        ]),
        "meta": {
            "user_id": random.choice([None, 1, 7, 42, 1337]),
            "duration_ms": random.randint(5, 1200),
        },
    }
    if lvl == "ERROR" and random.random() < 0.5:
        exc, msg = random.choice(EXCEPTIONS)
        payload["exception"] = {
            "type": exc,
            "message": msg,
            "stack": [
                "File \"app.py\", line 12, in route",
                "File \"service.py\", line 87, in process",
                "File \"db.py\", line 13, in query",
            ]
        }
    return json.dumps(payload, ensure_ascii=False) + "\n"

def nginx_line(error_ratio: float):
    ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
    method = random.choice(LEVELS and ["GET","POST","PUT","PATCH","DELETE"])
    path = random.choice(PATHS)
    status = random.choice(STATUS_BAD if random.random() < error_ratio else STATUS_GOOD)
    size = random.randint(128, 25000)
    rt = f"{random.uniform(0.001, 2.5):.3f}"
    ts = time.strftime("[%d/%b/%Y:%H:%M:%S +0000]", time.gmtime())
    ua = random.choice([
        "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
        "curl/8.1.2",
        "python-requests/2.31",
        "k6/0.46",
        "PostmanRuntime/7.39",
    ])
    return f'{ip} - - {ts} "{method} {path} HTTP/1.1" {status} {size} "-" "{ua}" {rt}\n'

def db_line(error_ratio: float):
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    if random.random() < error_ratio:
        msg = random.choice(DB_ERRORS)
        ctx = f"statement: SELECT * FROM items WHERE id={random.randint(1,9999)}"
    else:
        msg = "LOG: statement: SELECT 1"
        ctx = ""
    return f"{ts} {msg} {ctx}\n"

def system_line(error_ratio: float):
    ts = datetime.utcnow().strftime('%b %d %H:%M:%S')
    host = "host01"
    unit = random.choice(["web.service","worker.service","db.service"])
    lvl = random.choice(["INFO","WARN","ERROR"] if random.random() < error_ratio else ["INFO"])
    msg = random.choice([
        "Started Service",
        "Shutting down",
        "Healthcheck failed",
        "Restarting (exit status 1)",
        "Configuration reload triggered",
    ])
    return f"{ts} {host} {unit}[{random.randint(100,999)}]: {lvl} {msg}\n"

def k8s_line(error_ratio: float):
    lvl = "ERROR" if random.random() < error_ratio else random.choice(["INFO","WARN"])
    rid = rand_req_id()
    payload = {
        "ts": now_iso(),
        "level": lvl,
        "msg": random.choice([
            "probe failed",
            "pod restarted",
            "backoff restarting failed container",
            "image pull",
            "request served",
        ]),
        "kubernetes": {
            "pod_name": random.choice(["web-abc123","worker-def456","api-ghi789"]),
            "namespace_name": random.choice(["prod","staging","dev"]),
            "container_name": random.choice(["app","sidecar","init"]),
            "host": random.choice(["node-a","node-b","node-c"]),
        },
        "rid": rid,
        "path": random.choice(PATHS),
        "status": random.choice([200, 204, 400, 401, 404, 409, 500, 502, 503]),
    }
    if lvl == "ERROR" and random.random() < 0.5:
        exc, msg = random.choice(EXCEPTIONS)
        payload["exception"] = {
            "type": exc,
            "message": msg,
            "stack": [
                "File \"app.py\", line 42, in handle_request",
                "File \"service.py\", line 87, in process",
                "File \"db.py\", line 13, in query",
            ]
        }
    return json.dumps(payload, ensure_ascii=False) + "\n"

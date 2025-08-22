# LOGS_TRAINING_MANUAL.md
Практическая методичка по работе с логами из терминала (QA/DevOps edition)

Эта шпаргалка заточена под тренировочный полигон `log-simulator` (app/plain, JSON, nginx, DB, systemd-style, k8s),
но одинаково полезна для реальных проектов. Все рецепты — однострочники, которые легко встраиваются в CI.

**Инструменты, которые пригодятся**
- `ripgrep (rg)`, `grep`, `awk`, `sed`, `cut`, `sort`, `uniq`, `watch`
- `jq` (JSON), `jq -r` для сырого вывода
- `less -R` (цветной вывод), `ccze`, `lnav` (приятный просмотр)
- `gzip`/`zstd` + `zgrep`/`zstdcat`/`zstdless`
- Дополнительно: `pv` (скорость потока), `parallel` (GNU), `datamash` (удобная статистика)

```bash
# macOS (Homebrew) — базовый набор
brew install ripgrep jq zstd pv gnu-parallel
# Debian/Ubuntu
sudo apt update && sudo apt install -y ripgrep jq zstd pv parallel
```

---

## 1) БЫСТРЫЙ ПОИСК ОШИБОК В РАЗНЫХ ФОРМАТАХ

### 1.1 Plain app-логи (`logs/app/app.log`)
```bash
# Живой поток только WARN/ERROR
tail -F logs/app/app.log | grep --line-buffered -E --color=always "ERROR|WARN"

# Последние 5000 строк: топ повторяющихся ошибок (нормализуем числа/UUID)
tail -n 5000 logs/app/app.log | rg "ERROR" | sed -E 's/[0-9a-f-]{8,}/UUID/g; s/\b[0-9]{3,}\b/NUM/g' | sort | uniq -c | sort -nr | head
```

Искать по `request-id` (например, `rid=RID-1234abcd`):
```bash
rg -n "rid=RID-1234abcd" logs/app/app.log -C2
```

Вытянуть timestamp + уровень + сообщение (если формат "YYYY-mm-dd HH:MM:SS LEVEL rid=... MSG"):
```bash
awk '{printf "%s %s %s\n", $1" "$2, $3, substr($0, index($0,$5))}' logs/app/app.log | head
```

### 1.2 JSON-логи (`logs/json/app.jsonl`)
```bash
# Только ERROR (ts + msg)
jq -r 'select(.level=="ERROR") | .ts + " " + .msg' logs/json/app.jsonl | head

# Поиск по request-id с красивым выводом:
RID=RID-1234abcd
jq -r "select(.rid==\"$RID\") | [.ts,.level,.msg] | @tsv" logs/json/app.jsonl
```

Вытащить ERROR с исключением и стеком:
```bash
jq -r 'select(.level=="ERROR" and .exception) | .ts, .exception.type, .exception.message, (.exception.stack[]?)' logs/json/app.jsonl | less
```

### 1.3 Nginx access (`logs/nginx/access.log`)
```bash
# 5xx в реальном времени
tail -F logs/nginx/access.log | rg --line-buffered ' "HTTP/1\.[01]" 5[0-9][0-9] '

# Топ эндпоинтов с 5xx
awk '$9 ~ /^5/ {print $7}' logs/nginx/access.log | sort | uniq -c | sort -nr | head

# Счётчик 4xx/5xx
awk '{c[$9]++} END{for (k in c) printf "%s %d\n", k, c[k]}' logs/nginx/access.log | sort -n
```

### 1.4 DB-логи (`logs/db/db.log`)
```bash
# Частые DB-проблемы
rg -n "deadlock|duplicate key|timeout|could not serialize|FATAL" logs/db/db.log

# Вытянуть timestamp и текст ошибки
awk '$0 ~ /ERROR|FATAL/ {print $1" "$2, substr($0,index($0,$3))}' logs/db/db.log | head
```

### 1.5 systemd-style (`logs/system/sys.log`)
```bash
# Последние ошибки конкретного юнита
rg -n "web\.service\[[0-9]+\]: (WARN|ERROR)" logs/system/sys.log -C1

# Счётчик по уровням
rg -o " (INFO|WARN|ERROR) " logs/system/sys.log | sort | uniq -c
```

### 1.6 k8s JSON (`logs/k8s/pod.log`)
```bash
# Ошибки по namespace=prod
jq -r 'select(.level=="ERROR" and .kubernetes.namespace_name=="prod") | [.ts,.kubernetes.pod_name,.msg] | @tsv' logs/k8s/pod.log | head

# Трассировка по request-id
RID=RID-1234abcd
jq -r "select(.rid==\"$RID\") | .ts+\" \" + .level + \" \" + .msg" logs/k8s/pod.log
```

### 1.7 Массовый поиск по всем форматам
```bash
# Найти «Traceback»/Exception во всех логах
rg -n "Traceback|Exception|ERROR" logs/** -S
```

---

## 2) АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ (p50/p95/p99)

### 2.1 Nginx (время ответа — последнее поле, как `0.123`)
```bash
# p95
awk '{print $NF}' logs/nginx/access.log | sort -n | awk 'BEGIN{n=0} {a[++n]=$1} END{if(n){idx=int(0.95*n); if(idx<1) idx=1; print a[idx]} else print "no data"}'

# p99
awk '{print $NF}' logs/nginx/access.log | sort -n | awk 'BEGIN{n=0} {a[++n]=$1} END{if(n){idx=int(0.99*n); if(idx<1) idx=1; print a[idx]} else print "no data"}'
```

p95 по каждому эндпоинту:
```bash
awk '{print $7, $NF}' logs/nginx/access.log | sort -k1,1 -k2,2n | awk '
  BEGIN{cur=""; n=0}
  {
    if ($1!=cur && cur!="") { idx=int(0.95*n); if(idx<1) idx=1; print cur, a[idx]; delete a; n=0 }
    cur=$1; a[++n]=$2
  }
  END{ if(n){ idx=int(0.95*n); if(idx<1) idx=1; print cur, a[idx] } }'
```

### 2.2 JSON (например, поле `.meta.duration_ms`)
```bash
jq -r '.meta.duration_ms // empty' logs/json/app.jsonl | sort -n | awk 'BEGIN{n=0} {a[++n]=$1} END{if(n){print "p95(ms)=",a[int(0.95*n)]}}'
```

### 2.3 Наблюдение «пульса» в реальном времени
```bash
# Кол-во 5xx в минуту (скользящее окно из последних 3000 строк)
watch -n 2 'tail -n 3000 logs/nginx/access.log | rg -c " 5[0-9][0-9] "'
```

> ⚠️ Для **очень больших** файлов см. раздел 5: используйте разбиение + параллель, чтобы не сортировать гигабайты целиком.

---

## 3) РАБОТА СО СЖАТЫМИ ЛОГАМИ (.gz, .zst)

### 3.1 Быстрый просмотр
```bash
# Gzip
zgrep -n "ERROR" logs/app/app.log.20250821.gz | head
zcat logs/app/app.log.20250821.gz | less -R

# Zstandard
zstdcat logs/k8s/pod.log.20250821.zst | rg -n "ERROR" | head
# если есть zstdless:
zstdless logs/k8s/pod.log.20250821.zst
```

### 3.2 Анализ в потоке (без распаковки на диск)
```bash
zstdcat logs/nginx/access.log.*.zst | awk '$9 ~ /^5/ {print $7}' | sort | uniq -c | sort -nr | head
zcat logs/json/app.jsonl.*.gz | jq -r 'select(.level=="ERROR") | .msg' | sort | uniq -c | sort -nr | head
```

### 3.3 Смешанные форматы (несколько файлов)
```bash
# Все ротации + текущие
( cat logs/app/app.log; zcat logs/app/app.log.*.gz 2>/dev/null; zstdcat logs/app/app.log.*.zst 2>/dev/null ) | rg -n "ERROR" | wc -l
```

---

## 4) АНАЛИЗ БЕЗОПАСНОСТИ И ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ

### 4.1 Nginx: брутфорс/сканирование
```bash
# Топ IP с 401/403
awk '$9 ~ /^(401|403)$/{print $1}' logs/nginx/access.log | sort | uniq -c | sort -nr | head

# Подозрительные пути (админка, .env, wp-скан и т.п.)
rg -n '/wp-admin|/wp-login|/\.git|/\.env|/etc/passwd|/phpmyadmin' logs/nginx/access.log
```

### 4.2 Подозрительные User-Agent'ы
```bash
rg -n '"(curl|wget|nikto|sqlmap|nmap)/' logs/nginx/access.log
```

### 4.3 Возможные инъекции / LFI / RCE (быстрые эвристики)
```bash
rg -n '(\.\./|\bUNION\b|\bSLEEP\(|;.*(cat|ls|sh)\b|cmd=|`.+`)' logs/** -i -S
```

### 4.4 JSON: частые «authorization failed» по user_id
```bash
jq -r 'select(.msg=="authorization failed") | .meta.user_id' logs/json/app.jsonl | sort | uniq -c | sort -nr
```

### 4.5 K8s: рестарты подов / backoff
```bash
jq -r 'select(.msg|test("backoff|restarted|probe failed";"i")) | [.ts,.kubernetes.pod_name,.msg] | @tsv' logs/k8s/pod.log | head
```

> ⚠️ Эвристики дают «подсветку», не приговор. Всегда проверяйте контекст и сопутствующие логи приложения/БД.

---

## 5) РАБОТА С ОЧЕНЬ БОЛЬШИМИ ЛОГАМИ

**Принципы скорости:**
- Используйте **потоки** и **пайплайны** — не пишите промежуточные файлы, если не нужно.
- Ускоряйте сортировку: `LC_ALL=C sort -S 50% -T /tmp` (более быстрая локаль, больше RAM, отдельный tmp).
- Где можно — считайте **приближённо** (см. histograms), либо сортируйте **по частям**.

### 5.1 Разбиение + параллель
```bash
# Разбить на чанки по ~100МБ и параллельно посчитать 5xx на каждый
split -b 100m logs/nginx/access.log /tmp/nginx.part.
parallel --will-cite "awk '\''$9 ~ /^5/ {print $7}'\'' {} | sort | uniq -c" ::: /tmp/nginx.part.* | awk '{c[$2]+=$1} END{for (k in c) printf "%7d %s\n", c[k], k}' | sort -nr | head
```

### 5.2 Грубый перцентиль без полной сортировки (гистограмма)
```bash
# Квантиль по бинам (пример: nginx rt в секундах, бин шириной 0.01)
awk '{
  v=$NF+0; b=int(v*100); hist[b]++ ; total++
} END{
  want=total*0.95; cur=0;
  for(i=0;i<100000;i++){ if(hist[i]){ cur+=hist[i]; if(cur>=want){ printf "p95≈%.2f\n", i/100; break } } }
}' logs/nginx/access.log
```

### 5.3 Интерактивный просмотр «на лету»
```bash
# Без «затыков» пайплайна:
stdbuf -oL -eL rg -n "ERROR" logs/** | less -R
```

### 5.4 Прогресс обработки
```bash
pv logs/nginx/access.log | rg -n " 5[0-9][0-9] " | wc -l
```

---

## 6) ПОЛЕЗНЫЕ ШАБЛОНЫ И АЛИАСЫ

Добавьте в `~/.bashrc` или `~/.zshrc`:

```bash
# Красный поток ошибок
logerr() { tail -F "$1" | grep --line-buffered --color=always -E "ERROR|WARN"; }

# Топ нормализованных ошибок
logtop() {
  rg "ERROR" "$1" | sed -E 's/[0-9a-f-]{8,}/UUID/g; s/\b[0-9]{3,}\b/NUM/g'   | sort | uniq -c | sort -nr | head
}

# p95 из nginx access.log (по последнему полю)
p95() {
  awk '{print $NF}' "$1" | sort -n | awk 'BEGIN{n=0}{a[++n]=$1}END{if(n){idx=int(0.95*n); if(idx<1) idx=1; print a[idx]} }'
}

# Поиск по request-id сразу во всех форматах
ridfind() { rg -n "$1" logs/** -S; }

# Безопасный репорт (редакция PII)
san() {
  rg -n "" "$1" | sed -E 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<email>/g; s/\b[0-9]{6,}\b/<num>/g'
}
```

---

## 7) РАБОТА С РОТАЦИЕЙ

```bash
# Следить за текущим файлом, даже если он был переименован ротатором:
tail -F logs/app/app.log

# Собрать все ротации и текущий в один поток:
( cat logs/app/app.log; zcat logs/app/app.log.*.gz 2>/dev/null; zstdcat logs/app/app.log.*.zst 2>/dev/null ) | rg -n "ERROR"
```

---

## 8) ИНТЕГРАЦИЯ В CI/CD

Проваливать сборку при наличии ошибок:
```bash
ERR=$(rg -c "ERROR|Exception" logs/** || true)
if [ "${ERR:-0}" -gt 0 ]; then
  echo "Found $ERR errors"; exit 1
fi
```

Сохранять артефакт «выжимка ошибок»:
```bash
rg -n "ERROR|Exception|Traceback" logs/** > artifacts/errors.log || true
```

---

## 9) ЧТО СМОТРЕТЬ ПРИ ИНЦИДЕНТЕ (чек-лист)

1. **Есть ли всплеск 5xx/4xx?**  
   `watch -n 2 'tail -n 5000 logs/nginx/access.log | rg -c " 5[0-9][0-9] "'`
2. **Какой эндпоинт/сервис лидирует по ошибкам?**  
   `awk '$9 ~ /^5/ {print $7}' logs/nginx/access.log | sort | uniq -c | sort -nr | head`
3. **Есть ли «красная нить» (request-id)?**  
   `rg -n "RID-...." logs/** -S`
4. **Исключения/Traceback в приложении/JSON/k8s?**  
   `rg -n "Traceback|Exception" logs/** -S`
5. **DB: deadlock/timeout/serialization?**  
   `rg -n "deadlock|timeout|could not serialize" logs/db/db.log`
6. **p95/p99 уползли?** (nginx/JSON) — см. раздел 2.
7. **Маршрутизация/подозрительные агенты/боты?** — см. раздел 4.

Удачи в охоте за багами 🔎

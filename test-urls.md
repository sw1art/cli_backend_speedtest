# Тестовые URL для ручной проверки

Готового пакета с URL нет, но для ручного теста хватает этих стабильных
«тестовых файлов». Перед использованием проверьте доступность (адреса
классические, но у внешних сервисов бывают изменения).

## 1. Публичные тестовые файлы (нужен интернет)

### Hetzner (Европа, очень стабильные)
```
https://speed.hetzner.de/1MB.bin
https://speed.hetzner.de/10MB.bin
https://speed.hetzner.de/100MB.bin
https://speed.hetzner.de/1GB.bin
```

### thinkbroadband (Великобритания, классика)
```
https://download.thinkbroadband.com/5MB.zip
https://download.thinkbroadband.com/10MB.zip
https://download.thinkbroadband.com/100MB.zip
https://download.thinkbroadband.com/1GB.zip
```

### OVH
```
https://proof.ovh.net/files/1Mb.dat
https://proof.ovh.net/files/10Mb.dat
https://proof.ovh.net/files/100Mb.dat
https://proof.ovh.net/files/1Gb.dat
```

### Cloudflare (объём задаётся параметром `bytes`)
```
https://speed.cloudflare.com/__down?bytes=10000000    # 10 MB
https://speed.cloudflare.com/__down?bytes=100000000   # 100 MB
```

### httpbin (маленькие ответы, удобно для проверки ошибок/статусов)
```
https://httpbin.org/bytes/1048576   # 1 MB случайных байт
https://httpbin.org/image/jpeg      # картинка
https://httpbin.org/status/404      # тест обработки HTTP-ошибок
```

## 2. Локальный вариант (самый надёжный, без интернета)

Поднимите локальный статический сервер и «тяжёлый» файл:

```powershell
# 1. создать файл ~20 МБ
python -c "open('big.bin','wb').write(b'x'*20971520)"

# 2. поднять сервер на 127.0.0.1:8123
python -m http.server 8123

# 3. в другом терминале — замер
cd cli
.venv\Scripts\python.exe -m download_benchmark http://127.0.0.1:8123/big.bin -n 5
```

## 3. Примеры запуска CLI

```powershell
cd cli

# 10 запросов (по умолчанию)
.venv\Scripts\python.exe -m download_benchmark https://speed.hetzner.de/10MB.bin

# 5 запросов, таймаут 15 секунд
.venv\Scripts\python.exe -m download_benchmark -n 5 -t 15 https://speed.hetzner.de/10MB.bin

# JSON-вывод (удобно для скриптов)
.venv\Scripts\python.exe -m download_benchmark --json https://speed.hetzner.de/10MB.bin
```

## 4. Примеры для Backend (curl)

Если стек ещё не запущен:

```powershell
cd backend
docker compose up -d
```

Создать задачу (worker скачает URL и посчитает статистику):

```powershell
curl -X POST http://localhost:8000/api/v1/tasks `
  -H "Content-Type: application/json" `
  -d '{\"url\": \"https://speed.hetzner.de/10MB.bin\", \"total_requests\": 5}'
```

Из ответа возьмите `id`, затем:

```powershell
# статус (PENDING -> PROCESSING -> COMPLETED/FAILED)
curl http://localhost:8000/api/v1/tasks/<ID>

# результаты + статистика
curl http://localhost:8000/api/v1/tasks/<ID>/results

# список всех задач
curl http://localhost:8000/api/v1/tasks
```

Либо откройте Swagger UI и тестируйте кнопками: <http://localhost:8000/docs>

## Примечание

- Для **Backend** worker качает URL изнутри Docker-сети, поэтому нужен публичный
  адрес (или `http://host.docker.internal:8123/...`, если файл отдаёт локальный
  сервер на хосте).
- Значение `total_requests` в API ограничено диапазоном 1–100.
- Статус `FAILED` получится, например, на `https://httpbin.org/status/404`
  (все запросы вернут 404) или на недоступном хосте.

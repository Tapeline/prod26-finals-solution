# Примеры эксплуатационной готовности

## Метрики

Сервис экспортирует служебные метрики http запросов, а также ряд бизнес метрик:

- Counter `processed_events_count` — количество обработанных событий
- Counter `newly_made_decision_count` — количество принятых решений по флагам 
  (количество **новых** выдач).

Пример ответа `/_internal/metrics`:

```
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 133238.0
python_gc_objects_collected_total{generation="1"} 24573.0
python_gc_objects_collected_total{generation="2"} 2692.0
# HELP python_gc_objects_uncollectable_total Uncollectable objects found during GC
# TYPE python_gc_objects_uncollectable_total counter
python_gc_objects_uncollectable_total{generation="0"} 0.0
python_gc_objects_uncollectable_total{generation="1"} 0.0
python_gc_objects_uncollectable_total{generation="2"} 0.0
# HELP python_gc_collections_total Number of times this generation was collected
# TYPE python_gc_collections_total counter
python_gc_collections_total{generation="0"} 265.0
python_gc_collections_total{generation="1"} 24.0
python_gc_collections_total{generation="2"} 2.0
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="13",patchlevel="12",version="3.13.12"} 1.0
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 7.805952e+08
# HELP process_resident_memory_bytes Resident memory size in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 2.1157888e+08
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 1.77185590986e+09
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 9.82
# HELP process_open_fds Number of open file descriptors.
# TYPE process_open_fds gauge
process_open_fds 28.0
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 1.048576e+06
# HELP litestar_requests_in_progress Total requests currently in progress
# TYPE litestar_requests_in_progress gauge
litestar_requests_in_progress{app_name="alphabet",method="GET",path="/api/v1/guardrails/{rule_id}",status_code="200"} 0.0
# и другие пути
# HELP litestar_requests_total Total requests
# TYPE litestar_requests_total counter
litestar_requests_total{app_name="alphabet",method="GET",path="/api/v1/guardrails/{rule_id}",status_code="200"} 1.0
# и другие пути
# HELP litestar_requests_created Total requests
# TYPE litestar_requests_created gauge
litestar_requests_created{app_name="alphabet",method="GET",path="/api/v1/guardrails/{rule_id}",status_code="200"} 1.7718560130513508e+09
# и другие пути
# HELP litestar_request_duration_seconds Request duration, in seconds
# TYPE litestar_request_duration_seconds histogram
litestar_request_duration_seconds_bucket{app_name="alphabet",le="+Inf",method="GET",path="/api/v1/guardrails/{rule_id}",status_code="200"} 1.0
# и другие пути
# HELP litestar_request_duration_seconds_created Request duration, in seconds
# TYPE litestar_request_duration_seconds_created gauge
litestar_request_duration_seconds_created{app_name="alphabet",method="GET",path="/api/v1/guardrails/{rule_id}",status_code="200"} 1.7718560130513744e+09
# и другие пути
# HELP newly_made_decision_count_total Newly made decision count
# TYPE newly_made_decision_count_total counter
newly_made_decision_count_total 1019.0
# HELP newly_made_decision_count_created Newly made decision count
# TYPE newly_made_decision_count_created gauge
newly_made_decision_count_created 1.7718559720145776e+09
# HELP processed_events_count_total Processed events count
# TYPE processed_events_count_total counter
processed_events_count_total 538.0
# HELP processed_events_count_created Processed events count
# TYPE processed_events_count_created gauge
processed_events_count_created 1.7718559963502755e+09
```

## Структурированные логи

Сервис ведёт логирование в prod-контейнере в формате JSON (за исключением служебных
сообщений, не поддающихся форматированию).

В каждый лог, порождённый HTTP-запросом, включен уникальный `request_id`, чтобы
было проще отслеживать путь каждого запроса.

Пример логов:

```
{"path": "/api/v1/events/receive", "method": "POST", "content_type": ["application/json", {}], "headers": {"host": "localhost:8000", "accept": "*/*", "accept-encoding": "gzip, deflate, zstd", "connection": "keep-alive", "user-agent": "python-httpx/0.28.1", "content-length": "211", "content-type": "application/json"}, "cookies": {}, "query": {}, "path_params": {}, "body": {"events": [{"event_id": "evt_exposure_1", "event_type": "exposure_b4_4", "decision_id": "019c8ad8-e8b4-753d-b88b-ffe19803ced3:flag_b4_4:user_1:treatment", "payload": {}, "issued_at": "2026-02-23T14:13:17.287209+00:00"}]}, "event": "HTTP Request", "request_id": "a143d7d8-4597-4f2e-9b9e-6d639104be3b", "level": "info", "timestamp": "2026-02-23T14:13:17.305243"}
{"n": 1, "event": "Processing events", "request_id": "a143d7d8-4597-4f2e-9b9e-6d639104be3b", "level": "info", "timestamp": "2026-02-23T14:13:17.305458"}
{"duplicates": 1, "event": "Deduplicated", "request_id": "a143d7d8-4597-4f2e-9b9e-6d639104be3b", "level": "info", "timestamp": "2026-02-23T14:13:17.305830"}
{"ok": 1, "duplicates": 0, "errors": 0, "event": "Buffering received", "request_id": "a143d7d8-4597-4f2e-9b9e-6d639104be3b", "level": "info", "timestamp": "2026-02-23T14:13:17.306198"}
{"event": "192.168.65.1:36624 - \"POST /api/v1/events/receive HTTP/1.1\" 200", "level": "info", "logger": "uvicorn.access", "request_id": "a143d7d8-4597-4f2e-9b9e-6d639104be3b", "timestamp": "2026-02-23 14:13:17.306456", "thread": 139637758364608, "func_name": "send", "filename": "httptools_impl.py", "process_name": "MainProcess", "pathname": "/app/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/httptools_impl.py", "thread_name": "MainThread", "module": "httptools_impl", "process": 140, "client_addr": "192.168.65.1:36624", "http_method": "POST", "url": "/api/v1/events/receive", "http_version": "1.1", "status_code": 200}
{"status_code": 200, "cookies": {}, "headers": {"content-type": "application/json", "content-length": "46"}, "body": "{\"ok_count\":1,\"duplicate_count\":0,\"errors\":{}}", "event": "HTTP Response", "request_id": "a143d7d8-4597-4f2e-9b9e-6d639104be3b", "level": "info", "timestamp": "2026-02-23T14:13:17.306601"}
{"path": "/api/v1/events/receive", "method": "POST", "content_type": ["application/json", {}], "headers": {"host": "localhost:8000", "accept": "*/*", "accept-encoding": "gzip, deflate, zstd", "connection": "keep-alive", "user-agent": "python-httpx/0.28.1", "content-length": "216", "content-type": "application/json"}, "cookies": {}, "query": {}, "path_params": {}, "body": {"events": [{"event_id": "evt_click_1", "event_type": "click_b4_4", "decision_id": "019c8ad8-e8b4-753d-b88b-ffe19803ced3:flag_b4_4:user_1:treatment", "payload": {"value": 100}, "issued_at": "2026-02-23T14:13:17.307528+00:00"}]}, "event": "HTTP Request", "request_id": "24b10ced-4fc0-40ca-bb1c-673ff362559c", "level": "info", "timestamp": "2026-02-23T14:13:17.324503"}
{"n": 1, "event": "Processing events", "request_id": "24b10ced-4fc0-40ca-bb1c-673ff362559c", "level": "info", "timestamp": "2026-02-23T14:13:17.324719"}
{"duplicates": 1, "event": "Deduplicated", "request_id": "24b10ced-4fc0-40ca-bb1c-673ff362559c", "level": "info", "timestamp": "2026-02-23T14:13:17.325136"}
{"ok": 1, "duplicates": 0, "errors": 0, "event": "Buffering received", "request_id": "24b10ced-4fc0-40ca-bb1c-673ff362559c", "level": "info", "timestamp": "2026-02-23T14:13:17.325613"}
{"event": "192.168.65.1:63433 - \"POST /api/v1/events/receive HTTP/1.1\" 200", "level": "info", "logger": "uvicorn.access", "request_id": "24b10ced-4fc0-40ca-bb1c-673ff362559c", "timestamp": "2026-02-23 14:13:17.325881", "thread": 139637758364608, "func_name": "send", "filename": "httptools_impl.py", "process_name": "MainProcess", "pathname": "/app/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/httptools_impl.py", "thread_name": "MainThread", "module": "httptools_impl", "process": 140, "client_addr": "192.168.65.1:63433", "http_method": "POST", "url": "/api/v1/events/receive", "http_version": "1.1", "status_code": 200}
{"status_code": 200, "cookies": {}, "headers": {"content-type": "application/json", "content-length": "46"}, "body": "{\"ok_count\":1,\"duplicate_count\":0,\"errors\":{}}", "event": "HTTP Response", "request_id": "24b10ced-4fc0-40ca-bb1c-673ff362559c", "level": "info", "timestamp": "2026-02-23T14:13:17.326058"}
{"path": "/health", "method": "GET", "content_type": ["", {}], "headers": {"host": "localhost:8000", "user-agent": "curl/8.14.1", "accept": "*/*"}, "cookies": {}, "query": {}, "path_params": {}, "body": null, "event": "HTTP Request", "request_id": "9ca86dbe-8aaf-4b71-978e-1064cae0bd7e", "level": "info", "timestamp": "2026-02-23T14:13:17.952396"}
{"event": "127.0.0.1:38746 - \"GET /health HTTP/1.1\" 200", "level": "info", "logger": "uvicorn.access", "request_id": "9ca86dbe-8aaf-4b71-978e-1064cae0bd7e", "timestamp": "2026-02-23 14:13:17.952684", "thread": 139637758364608, "func_name": "send", "filename": "httptools_impl.py", "process_name": "MainProcess", "pathname": "/app/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/httptools_impl.py", "thread_name": "MainThread", "module": "httptools_impl", "process": 140, "client_addr": "127.0.0.1:38746", "http_method": "GET", "url": "/health", "http_version": "1.1", "status_code": 200}
{"status_code": 200, "cookies": {}, "headers": {"content-type": "text/plain; charset=utf-8", "content-length": "7"}, "body": "healthy", "event": "HTTP Response", "request_id": "9ca86dbe-8aaf-4b71-978e-1064cae0bd7e", "level": "info", "timestamp": "2026-02-23T14:13:17.952811"}
{"event": "Regular guardrail check begin", "level": "info", "timestamp": "2026-02-23T14:13:18.114297"}
{"elapsed_s": 0.003604888916015625, "rules_checked": 0, "experiments_checked": 1, "event": "Regular guardrail check finished", "level": "info", "timestamp": "2026-02-23T14:13:18.118027"}
{"event": "Running attribution cycle", "level": "info", "timestamp": "2026-02-23T14:13:18.580075"}
{"to_write": 7, "ok": 4, "err": 2, "dup": 1, "event": "Flushing events from routine", "level": "info", "timestamp": "2026-02-23T14:13:19.002066"}
{"to_write": 4, "event": "Flushing conflict resolutions from routine", "level": "info", "timestamp": "2026-02-23T14:13:19.002836"}
{"to_write": 21, "event": "Flushing assignments from routine", "level": "info", "timestamp": "2026-02-23T14:13:19.056043"}
{"event": "Regular guardrail check begin", "level": "info", "timestamp": "2026-02-23T14:13:20.121336"}
{"elapsed_s": 0.004456043243408203, "rules_checked": 0, "experiments_checked": 1, "event": "Regular guardrail check finished", "level": "info", "timestamp": "2026-02-23T14:13:20.125951"}
{"event": "Running attribution cycle", "level": "info", "timestamp": "2026-02-23T14:13:20.597206"}
{"event": "Regular guardrail check begin", "level": "info", "timestamp": "2026-02-23T14:13:22.129283"}
{"elapsed_s": 0.0027589797973632812, "rules_checked": 0, "experiments_checked": 1, "event": "Regular guardrail check finished", "level": "info", "timestamp": "2026-02-23T14:13:22.132146"}
{"event": "Running attribution cycle", "level": "info", "timestamp": "2026-02-23T14:13:22.614172"}
{"path": "/health", "method": "GET", "content_type": ["", {}], "headers": {"host": "localhost:8000", "user-agent": "curl/8.14.1", "accept": "*/*"}, "cookies": {}, "query": {}, "path_params": {}, "body": null, "event": "HTTP Request", "request_id": "a7ca4abc-986f-4c35-9d50-58212619e9ad", "level": "info", "timestamp": "2026-02-23T14:13:22.996367"}
{"event": "127.0.0.1:38752 - \"GET /health HTTP/1.1\" 200", "level": "info", "logger": "uvicorn.access", "request_id": "a7ca4abc-986f-4c35-9d50-58212619e9ad", "timestamp": "2026-02-23 14:13:22.996679", "thread": 139637758364608, "func_name": "send", "filename": "httptools_impl.py", "process_name": "MainProcess", "pathname": "/app/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/httptools_impl.py", "thread_name": "MainThread", "module": "httptools_impl", "process": 140, "client_addr": "127.0.0.1:38752", "http_method": "GET", "url": "/health", "http_version": "1.1", "status_code": 200}

```

Пример того, что не будет отформатировано:

```
   Building alphabet-backend @ file:///app
      Built alphabet-backend @ file:///app
Uninstalled 1 package in 10ms
Installed 1 package in 2ms
Bytecode compiled 4286 files in 250ms
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
Bytecode compiled 4286 files in 171ms
Bytecode compiled 4286 files in 211ms
Bytecode compiled 4286 files in 195ms
Bytecode compiled 4286 files in 241ms
2026-02-23 14:11:53 [info     ] Bootstrapping the application
```


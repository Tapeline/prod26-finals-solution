# B5. Устойчивость и safety-механики

## B5-1, B5-2 Параметры guardrail

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

=== "curl"

    ```sh
    curl -X 'GET' \
      'http://localhost:80/api/v1/guardrails/gr_error_check' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru'
    ```

=== "Ожидаемый результат"

    ```
    {
      "id": "gr_error_check",
      "experiment_id": "019c8f72-9f92-7f22-8faa-0000000000e4",
      "metric_key": "errors",
      "threshold": 1,
      "watch_window_s": 3209600,
      "action": "pause",
      "is_archived": false
    }
    ```

## B5-3, B5-4, B5-5 Обнаружение -> действие -> лог

Получим решение для эксперимента с guardrail:

```sh
curl -X 'POST' \
  'http://localhost:80/api/v1/decisions/get-flags' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "subject_id": "u-b5-3",
  "attributes": {},
  "flags": [
    "flag_guard"
  ]
}'
```

Возьмём decision_id из ответа (допустим, это 
`019c8f72-9f92-7f22-8faa-0000000000e4:flag_guard:u-b5-3:risky`).

Пошлём несколько (2+) событий `error` (threshold небольшой для тестирования).

```sh
curl -X 'POST' \
  'http://localhost:80/api/v1/events/receive' \
  -H 'accept: application/json' \
  -H 'X-User-Id: exp' \
  -H 'X-User-Email: exp@t.ru' \
  -H 'Content-Type: application/json' \
  -d '{
  "events": [
    {
      "event_id": "some-unique-event-id-err-1",
      "event_type": "error",
      "decision_id": "019c8f72-9f92-7f22-8faa-0000000000e4:flag_guard:u-b5-3:risky",
      "payload": {},
      "issued_at": "2026-02-24T13:39:09.308Z"
    }
  ]
}'
```

Подождём 5-10 секунд. После этого запросим статус эксперимента.

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

=== "curl"

    ```sh
    curl -X 'GET' \
      'http://localhost:80/api/v1/experiments/019c8f72-9f92-7f22-8faa-0000000000e4' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru'
    ```

=== "Ожидаемый результат"

    ```
    { ..., "state": "paused", ...}

Запросим аудит.

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

=== "curl"

    ```sh
    curl -X 'GET' \
      'http://localhost:80/api/v1/guardrails/gr_error_check/log?limit=50&offset=0' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru'
    ```

=== "Ожидаемый результат"

    ```
    [
      {
        "id": "019c9017-eb7a-7133-a3bf-8273324d165b",
        "rule_id": "gr_error_check",
        "fired_at": "2026-02-24T14:40:12.655582",
        "experiment_id": "019c8f72-9f92-7f22-8faa-0000000000e4",
        "metric_key": "errors",
        "metric_value": 2,
        "taken_action": "pause"
      }
    ]
    ```

## B5-6 Ограничение постоянного участия

> В конфиге по умолчанию выставлен отдых в 15 с после 1 теста.

Используем флаг, например, `flag_active`. Возьмём subject_id `u-b5-6`.

Поучаствуем в, например, таргетированном эксперименте:

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/decisions/get-flags' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "subject_id": "u-b5-6",
      "attributes": {"country": "RU"},
      "flags": [
        "flag_targeted"
      ]
    }'
    ```

=== "Ожидаемый результат"

    Какой-то вариант

А затем быстро (в течение 15 с) попробуем поучаствовать в
другом, например, `flag_active`:

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/decisions/get-flags' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "subject_id": "u-b5-6",
      "attributes": {"country": "RU"},
      "flags": [
        "flag_active"
      ]
    }'
    ```

=== "Ожидаемый результат"

    ```sh
    {
      "flags": {
        "flag_active": {
          "id": ":flag_active:u-b5-6:!default-cooldown",
          "value": "blue",
          "experiment_id": null
        }
      }
    }
    ```

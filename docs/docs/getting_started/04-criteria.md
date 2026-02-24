# B4. События и атрибуция

Для тестов будем использовать один и тот же ID решения, предварительно
сгенерируем его, например, для флага `flag_active`:

```sh
curl -X 'POST' \
  'http://localhost:80/api/v1/decisions/get-flags' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "subject_id": "u-b4",
  "attributes": {},
  "flags": [
    "flag_active"
  ]
}'
```

Для каждого события будем стараться придумать уникальный ID,
иначе он будет воспринят как дубликат.

## B4-1 Валидация типов полей события

Используем тип события `check_types`. Его JSON Schema:

```json
{
  "type": "object",
  "properties": {
    "number": {
      "type": "number"
    }
  },
  "required": ["number"]
}
```

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/events/receive' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "events": [
        {
          "event_id": "some-unique-event-id-01",
          "event_type": "check_types",
          "decision_id": "019c8f72-9f92-7f22-8faa-0000000000e0:flag_active:u-b4:control",
          "payload": {
            "number": "not a number"
          },
          "issued_at": "2026-02-24T13:39:09.308Z"
        }
      ]
    }'
    ```

=== "Ожидаемый результат"

    ```
    {
      "ok_count": 0,
      "duplicate_count": 0,
      "errors": {
        "0": "bad_payload"
      }
    }
    ```

## B4-2 Валидация обязательных полей события

Используем тип события `check_required`. Его JSON Schema:

```json
{
  "type": "object",
  "properties": {
    "number": {
      "type": "number"
    }
  },
  "required": ["number"]
}
```

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/events/receive' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "events": [
        {
          "event_id": "some-unique-event-id-02",
          "event_type": "check_required",
          "decision_id": "019c8f72-9f92-7f22-8faa-0000000000e0:flag_active:u-b4:control",
          "payload": {},
          "issued_at": "2026-02-24T13:39:09.308Z"
        }
      ]
    }'
    ```

=== "Ожидаемый результат"

    ```
    {
      "ok_count": 0,
      "duplicate_count": 0,
      "errors": {
        "0": "bad_payload"
      }
    }
    ```

## B4-3 Дедупликация событий

!!! note
    Важно, что `exposure` будет отправлен хотя бы раз,
    это необходимо для последующих тестов атрибуции.

Используем тип события, например, `exposure`.
Два или более раза пошлём одно и то же событие.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/events/receive' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "events": [
        {
          "event_id": "some-unique-event-id-03",
          "event_type": "exposure",
          "decision_id": "019c8f72-9f92-7f22-8faa-0000000000e0:flag_active:u-b4:control",
          "payload": {},
          "issued_at": "2026-02-24T13:39:09.308Z"
        }
      ]
    }'
    ```

=== "Ожидаемый результат"

    Первый раз:

    ```
    {
      "ok_count": 1,
      "duplicate_count": 0,
      "errors": {}
    }
    ```

    Второй раз:

    ```
    {
      "ok_count": 0,
      "duplicate_count": 1,
      "errors": {}
    }
    ```

## B4-4, B4-5 Связь экспозиции с решением, атрибуция

!!! note
    Оба теста слиты в один, так как проверить B4-4 без B4-5
    можно только проинспектировав состояние базы данных.

Используем тип события `click`.

```sh
curl -X 'POST' \
  'http://localhost:80/api/v1/events/receive' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "events": [
    {
      "event_id": "some-unique-event-id-04",
      "event_type": "click",
      "decision_id": "019c8f72-9f92-7f22-8faa-0000000000e0:flag_active:u-b4:control",
      "payload": {},
      "issued_at": "2026-02-24T13:39:09.308Z"
    }
  ]
}'
```

Запросим ещё одно решение (как бы для другого субъекта):
сгенерируем его для этого же флага:

```sh
curl -X 'POST' \
  'http://localhost:80/api/v1/decisions/get-flags' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "subject_id": "u-b4-another",
  "attributes": {},
  "flags": [
    "flag_active"
  ]
}'
```

Используем тип события `click` (этот субъект ещё не отсылал exposure)

```sh
curl -X 'POST' \
  'http://localhost:80/api/v1/events/receive' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "events": [
    {
      "event_id": "some-unique-event-id-05",
      "event_type": "click",
      "decision_id": "019c8f72-9f92-7f22-8faa-0000000000e0:flag_active:u-b4-another:treatment",
      "payload": {},
      "issued_at": "2026-02-24T13:39:09.308Z"
    }
  ]
}'
```

Затем сделаем запрос к отчёту.

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

=== "curl"

    ```sh
    curl -X 'GET' \
      'http://localhost:80/api/v1/reports/019c8fed-7b54-7c86-80cc-f0769fa0a16c' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru'
    ```

=== "Ожидаемый результат"

    ```
    {
      "id": "019c8fed-7b54-7c86-80cc-f0769fa0a16c",
      "experiment_id": "019c8f72-9f92-7f22-8faa-0000000000e0",
      "start_at": "2026-02-20T13:53:37.713000",
      "end_at": "2026-03-18T13:53:37.713000",
      "metrics": [
        {
          "key": "ctr",
          "overall": 1,
          "per_variant": {
            "control": 1,
            "treatment": null
          }
        },
        {
          "key": "all_events",
          "overall": ...,
          "per_variant": {
            "control": ...,
            "treatment": ...
          }
        },
        {
          "key":"clicks",
          "overall": 1.0,
          "per_variant": {
            "control": ...,
            "treatment": ...
          }
        }
      ]
    }
    ```

Используем тип события `exposure` для послднего субъекта 
(должен атрибутировать ранее пришедший `click`).

```sh
curl -X 'POST' \
  'http://localhost:80/api/v1/events/receive' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "events": [
    {
      "event_id": "some-unique-event-id-06",
      "event_type": "exposure",
      "decision_id": "019c8f72-9f92-7f22-8faa-0000000000e0:flag_active:u-b4-another:treatment",
      "payload": {},
      "issued_at": "2026-02-24T12:39:09.308Z"
    }
  ]
}'
```

Затем сделаем запрос к отчёту.

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

=== "curl"

    ```sh
    curl -X 'GET' \
      'http://localhost:80/api/v1/reports/019c8fed-7b54-7c86-80cc-f0769fa0a16c' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru'
    ```

=== "Ожидаемый результат"

    ```
    {
      "id": "019c8fed-7b54-7c86-80cc-f0769fa0a16c",
      "experiment_id": "019c8f72-9f92-7f22-8faa-0000000000e0",
      "start_at": "2026-02-20T13:53:37.713000",
      "end_at": "2026-03-18T13:53:37.713000",
      "metrics": [
        {
          "key": "ctr",
          "overall": 1,
          "per_variant": {
            "control": 1,
            "treatment": null
          }
        },
        {
          "key": "all_events",
          "overall": ...,
          "per_variant": {
            "control": ...,
            "treatment": ...
          }
        },
        {
          "key":"clicks",
          "overall": 2.0,
          "per_variant": {
            "control": ...,
            "treatment": ...
          }
        }
      ]
    }
    ```

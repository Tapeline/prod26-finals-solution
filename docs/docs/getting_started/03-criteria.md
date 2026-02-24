# B3. Эксперименты: жизненный цикл и ревью

## B3-1 Переход draft -> in review

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

Используем эксперимент `019c8f72-9f92-7f22-8faa-0000000000e2`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/experiments/019c8f72-9f92-7f22-8faa-0000000000e2/send-to-review' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru' \
      -d ''
    ```

=== "Ожидаемый результат"

    ```
    {
      "id": "019c8f72-9f92-7f22-8faa-0000000000e2",
      "name": "Future Test",
      "flag_key": "flag_simple",
      "state": "in_review",
      "version": 1,
      "audience": 10,
      "variants": [
        {
          "name": "A",
          "value": "on",
          "is_control": false,
          "audience": 100
        }
      ],
      "targeting": null,
      "author_id": "019c8f72-9f92-7f22-8faa-000000000002",
      "created_at": "2026-02-24T12:41:41.083814",
      "updated_at": "2026-02-24T12:41:41.083814",
      "result": null,
      "metrics": {
        "primary": "ctr",
        "secondary": [],
        "guarding": []
      },
      "priority": null,
      "conflict_domain": null,
      "conflict_policy": null
    }
    ```

## B3-5 Одобрения только назначенных

!!! attention
    Выполняйте этот тест ДО теста на B3-2, так как они используют один
    и тот же эксперимент!

Используем учётные данные:

- `X-User-Id`: `approver2`
- `X-User-Email`: `approver2@t.ru`

Используем эксперимент `019c8f72-9f92-7f22-8faa-0000000000e3`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/experiments/019c8f72-9f92-7f22-8faa-0000000000e3/approve' \
      -H 'accept: application/json' \
      -H 'X-User-Id: approver2' \
      -H 'X-User-Email: approver2@t.ru' \
      -d ''
    ```

=== "Ожидаемый результат"

    ```
    {
      "code": "not_allowed",
      "extras": {
        "detail": "Your role does not allow you to do that"
      }
    }
    ```

## B3-3 Нельзя запустить без ревью

!!! attention
    Выполняйте этот тест ДО теста на B3-2, так как они используют один
    и тот же эксперимент!

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

Используем эксперимент `019c8f72-9f92-7f22-8faa-0000000000e3`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/experiments/019c8f72-9f92-7f22-8faa-0000000000e3/start' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru' \
      -d ''
    ```

=== "Ожидаемый результат"

    ```
    {
      "code": "cannot_transition",
      "extras": {
        "detail": "Cannot transition from in_review to started"
      }
    }
    ```

## B3-2 Переход in_review -> approved

Используем учётные данные:

- `X-User-Id`: `approver`
- `X-User-Email`: `approver@t.ru`

Используем эксперимент `019c8f72-9f92-7f22-8faa-0000000000e3`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/experiments/019c8f72-9f92-7f22-8faa-0000000000e3/approve' \
      -H 'accept: application/json' \
      -H 'X-User-Id: approver' \
      -H 'X-User-Email: approver@t.ru' \
      -d ''
    ```

=== "Ожидаемый результат"

    ```
    {
      "status": "accepted",
      "decision": {
        "experiment_id": "019c8f72-9f92-7f22-8faa-0000000000e3",
        "type": "accepted",
        "rejecter_id": null,
        "reject_comment": null
      }
    }
    ```

## B3-4 Недопустимые переходы

Попытаемся отклонить уже запущенный эксперимент

Используем учётные данные:

- `X-User-Id`: `approver`
- `X-User-Email`: `approver@t.ru`

Используем эксперимент `019c8f72-9f92-7f22-8faa-0000000000e0`

=== "curl"
    
    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/experiments/019c8f72-9f92-7f22-8faa-0000000000e0/reject' \
      -H 'accept: application/json' \
      -H 'X-User-Id: approver' \
      -H 'X-User-Email: approver@t.ru' \
      -H 'Content-Type: application/json' \
      -d '{
      "comment": "This is a bad experiment"
    }'
    ```

=== "Ожидаемый результат"

    ```
    {
      "code": "experiment_not_in_review",
      "extras": {
        "detail": "Experiment is not in review"
      }
    }
    ```

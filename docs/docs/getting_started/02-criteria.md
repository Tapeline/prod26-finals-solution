# B2. Feature Flags и выдача вариантов

## B2-1 Выдача дефолта

Используем флаг `flag_no_exp`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/decisions/get-flags' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
        "subject_id": "u-b2-1",
        "attributes": {},
        "flags": [
          "flag_no_exp"
        ]
      }'
    ```

=== "Ожидаемый результат"

    ```
    {
      "flags": {
        "flag_no_exp": {
          "id": ":flag_no_exp:u-b2-1:!default-not-set",
          "value": "default",
          "experiment_id": null
        }
      }
    }
    ```

## B2-2 Проваленный таргетинг

Используем `flag_targeted`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/decisions/get-flags' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "subject_id": "u-b2-2",
      "attributes": {"country":"US"},
      "flags": [
        "flag_targeted"
      ]
    }'
    ```

=== "Ожидаемый результат"

    ```
    {
      "flags": {
        "flag_targeted": {
          "id": ":flag_targeted:u-b2-2:!default-019c8f72-9f92-7f22-8faa-0000000000e1-target",
          "value": "default",
          "experiment_id": null
        }
      }
    }
    ```

## B2-3 Пройденный таргетинг

Используем `flag_targeted`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/decisions/get-flags' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "subject_id": "u-b2-3",
      "attributes": {"country":"RU"},
      "flags": [
        "flag_targeted"
      ]
    }'
    ```

=== "Ожидаемый результат"

    ```
    {
      "flags": {
        "flag_targeted": {
          "id": "019c8f72-9f92-7f22-8faa-0000000000e1:flag_targeted:u-b2-3:control",
          "value": какое-то значение,
          "experiment_id": "019c8f72-9f92-7f22-8faa-0000000000e1"
        }
      }
    }
    ```

## B2-4 Детерминизм

Используем флаг, например, `flag_simple`.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/decisions/get-flags' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "subject_id": "u-b2-4",
      "attributes": {},
      "flags": [
        "flag_simple"
      ]
    }'
    ```

=== "Ожидаемый результат"

    Один и тот же ответ вида:

    ```
    {
      "flags": {
        "flag_simple": {
          "id": что-то,
          "value": что-то,
          "experiment_id": что-то
        }
      }
    }
    ```

## B2-5 Распределение

Используем флаг, например, `flag_active`.
С каждым запросом меняем subject_id.

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/decisions/get-flags' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "subject_id": ???,
      "attributes": {},
      "flags": [
        "flag_active"
      ]
    }'
    ```

=== "Ожидаемый результат"

    +- поровну распределение между ответами blue и red

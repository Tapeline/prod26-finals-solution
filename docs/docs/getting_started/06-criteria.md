# B6. Отчётность и принятие решения

## B6-1, B6-2, B6-3 Отчёт по периоду и в разрезе выбранных метрик

!!! attention
    Критерии не соответствуют техническому заданию:

    Критерий:
    > Можно задать окно времени, и отчёт перестраивается.

    ТЗ:
    > продакт заранее фиксирует, за какой период мы смотрим эффект, 
    > чтобы потом не было “давай ещё недельку подождём, вдруг вырастет”.
    > Метрики считаются в заданном временном окне:
    > - от начала периода (включительно) до конца периода (не включительно).
    
    Для реализации выбрано поведение, описанное в ТЗ. Если нужно
    построить за другой отчётный период, создайте новый отчёт.

!!! attention
    Этот тест использует факт того, что ранее для эксперимента
    `019c8f72-9f92-7f22-8faa-0000000000e0` уже делались запросы
    событий в рамках тестов группы B4.

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

Используем эксперимент `019c8f72-9f92-7f22-8faa-0000000000e2`.

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
          "overall": ...,
          "per_variant": {
            "control": ...,
            "treatment": ...
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
          "key": "clicks",
          "overall": ...,
          "per_variant": {
            "control": ...,
            "treatment": ...
          }
        }
      ]
    }
    ```

    Список метрик берётся из соответствующего поля эксперимента.

## B6-4, B6-5 Фиксация исхода с обоснованием

Используем учётные данные:

- `X-User-Id`: `exp`
- `X-User-Email`: `exp@t.ru`

Используем эксперимент `019c8f72-9f92-7f22-8faa-0000000000e7`
(уже завершён к моменту тестирования).

=== "curl"

    ```sh
    curl -X 'POST' \
      'http://localhost:80/api/v1/experiments/019c8f72-9f92-7f22-8faa-0000000000e7/archive' \
      -H 'accept: application/json' \
      -H 'X-User-Id: exp' \
      -H 'X-User-Email: exp@t.ru' \
      -H 'Content-Type: application/json' \
      -d '{
      "outcome": "rollout_winner",
      "comment": "This turned out to be great!"
    }'
    ```

=== "Ожидаемый результат"

    ```
    {
      "id": "019c8f72-9f92-7f22-8faa-0000000000e7",
      "name": "Old Report",
      "flag_key": "flag_simple",
      "state": "archived",
      ...
      "result": {
        "comment": "This turned out to be great!",
        "outcome": "rollout_winner"
      },
      ...
    }
    ```

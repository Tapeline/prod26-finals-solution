# Автоматизация разработки

## Предусловие

Необходим установленный python, docker + docker compose и uv.

## Стиль кода

На проекте настроены автоматические линтинг и форматирование:

> Предусловие: `uv sync --group lint`

=== "just-команды"

    ```sh 
    cd alphabet-backend
    just check all   # прогнать все проверки
    just check style  # прогнать только проверки стиля кода
    just format  # отформатировать код
    ```

=== "Без just"

    Проверка стиля:

    ```sh 
    cd alphabet-backend
    uv run ruff check
    ```

    Форматирование:

    ```sh 
    cd alphabet-backend
    uv run ruff format
    uv run ruff check --fix
    ```

Для проверки стиля и форматирования используется Ruff.

## Проверка типов

> Предусловие: `uv sync --group lint`

На проекте настроена автоматическая проверка типов:

=== "just-команды"

    ```sh 
    cd alphabet-backend
    just check types  # проверить типы
    ```

=== "Без just"

    Проверка типов:

    ```sh 
    cd alphabet-backend
    uv run mypy src
    ```

Для проверки типов используется mypy в strict режиме с дополнительно
ужесточёнными правилами проверки.

## Архитектурные тесты

> Предусловие: `uv sync --group lint`

На проекте настроена автоматическая проверка соблюдения принципов архитектуры:

=== "just-команды"

    ```sh 
    cd alphabet-backend
    just check arch  # проверить архитектуру
    ```

=== "Без just"

    Проверка архитектуры:

    ```sh 
    cd alphabet-backend
    uv run lint-imports
    ```

## GitLab CI

Обозначенные проверки автоматически выполняются в GitLab CI на этапе lint.

## Тесты

Тесты в проекте делятся на три уровня:

- юнит
- интеграционные
- системные/приёмочные


Запуск юнит-тестов:

```sh
cd alphabet-backend
uv sync --group test
uv run pytest tests/unit
```

Запуск интеграционных тестов:

```sh
docker compose up -d clickhouse
cd alphabet-backend
uv sync --group test 
uv run pytest tests/integration
```

Запуск системных и приёмочных тестов:

!!! note
    Если у вас уже запущены сервисы, остановите все с помощью
    подкоманды down у docker compose, в противном случае получатся
    конфликты по портам.

```sh
docker compose -f docker-compose.autotest.yml up -d
cd sys-tests
uv run pytest
```

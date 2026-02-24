# Спецификация DSL оповещений

## Спецификация языка подключений к каналам связи

=== "EBNF"

    ```ebnf
    
    connection-string ::= 
        integration-type "://" 
        resource-string
    
    integration-type ::= regex [A-Za-z-_]+
    
    resource-string ::= regex .*
    
    ```

=== "Примеры"

    - Отослать в телеграм чат команды:
        
        `tg://-10003942345`

    - Уведомить заинтересованное лицо по почте:

        `email://external-reviewer@myconsulting.com`
    

В рамках MVP поддерживаются `integration-type`:

- `tg` — Телеграм
- `email` — Email через SMTP

## Спецификация языка триггеров

```ebnf

trigger ::=
    "experiment_lifecycle:" experiment-id |
    "experiment_lifecycle:*" |
    "guardrail:" guardrail-id

guardrail-id ::=
    regex [A-Za-z0-9-_]+

experiment-id ::=
    regex [A-Za-z0-9-_]+

```

`experiment_lifecycle:*` означает, что этот триггер будет применим ко всем экспериментам.


!!! see-also
    [Метаязык DSL](metalang.md)

## Спецификация шаблонов сообщений

Шаблоны сообщений используют язык Jinja.

Доступные параметры контекста:

=== "experiment_lifecycle"
    
    - `state` — новое состояние эксперимента
    - `id` — ID эксперимента

=== "guardrail"

    - `audit_id` — ID записи аудита
    - `rule_id` — ID сработавшего правила
    - `fired_at` — время срабатывания
    - `experiment_id` — ID эксперимента
    - `metric_key` — ID записи аудита
    - `metric_value` — ID записи аудита
    - `taken_action` — действие guardrail на эксперимент (`pause`, `force_control`)

=== "Для всех"

    - `iat` — время выпуска уведомления в формате ISO

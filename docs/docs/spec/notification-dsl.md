# Спецификация DSL оповещений

## Спецификация языка подключений к каналам связи

```ebnf

connection-string ::= 
    integration-type "://" 
    [ auth-string "@" ] 
    resource-string 
    [ param-list ]

integration-type ::= regex [A-Za-z-_]+

auth-string ::= urlencoded string

resource-string ::= urlencoded string

param-list ::=
    "?" param-name "=" param-value { "&" param-name "=" param-value }

param-name ::= urlencoded string

param-value ::= urlencoded string

```

В рамках MVP поддерживаются `integration-type`:

- `tg` — Телеграм
- `email` — Email через SMTP

!!! note
    `auth-string`, `resource-string`, `param-name`, `param-value` могут содержать
    любой текст. Интерпретация возложена на реализацию конкретной интеграции.

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


# DSL таргетирования

## Определение грамматики

```ebnf

expr ::=
    disj
    
disj ::=
    conj { "OR" conj }

conj ::=
    cmp { "AND" cmp }

cmp ::=
    unary { ("IN" | "NOT IN" | ">" | ">=" | "<" | "<=" | "==" | "!=") unary }

unary ::=
    { "NOT" } primary

primary ::=
    "(" expr ")" |
    collection |
    value

value ::=
    date |
    string |
    number |
    bool |
    name |
    "undefined"
    
collection ::= 
    "[" [ value ] { "," value } "]"

date ::=
    regex [0-9]{4}-[0-9]{2}-[0-9]{2}

string ::=
    string literal in double quotes with \" and \\ escape sequences support

number ::=
    regex [0-9]+(\.[0-9]+)?

name ::=
    regex [a-zA-Z-_][a-zA-Z0-9-_]*

bool ::=
    true | 
    false

```

## Правила вычисления

При любой возникшей ошибке вычисления, выражение становится равно `false`, а
такое событие логируется с уровнем ERROR.

Строки сравниваются лексикографически.

Даты сравниваются по годам, потом по месяцам, потом по дням.

Числа сравниваются с допустимой погрешностью 1e-9 (известная проблема 0.1 + 0.2 != 0.3).

Значения разных типов не равны между собой ни при каких обстоятельствах.

`>`, `<`, `>=`, `<=` сравнения неподдерживаемых типов приводят к ошибкам.

Любая операция с `undefined` результирует в `false`.

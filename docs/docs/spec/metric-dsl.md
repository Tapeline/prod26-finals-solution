# Описание DSL расчёта метрик


=== "EBNF sql-like"

    ```ebnf
    
    metric-expr ::=
        component ["/" component]

    component ::=
        aggregation [ source ] [ attribution ] event_type value [ filters ] |
        "count" [ source ] [ attribution ] event_type [ filters ]   
    
    aggregation ::=
        "sum" |
        "min" |
        "max" |
        "p50" |
        "p75" |
        "p90" |
        "p95" |
        "p99"
    
    quantile ::=
        regex [0-9]{1,2}
    
    source ::=  # events by default
        "discarded" |
        "duplicate"
    
    attribution ::=  # all by default
        "attributed" |
        "unattributed" |
    
    event_type ::=
        regex [A-Za-z0-9_-]+ |
        "*"
    
    filters ::=
        "where" filter_disj
        
    filter_disj ::=
        filter_conj { "or" filter_conj }
    
    filter_conj ::=
        filter_primary { "and" filter_primary }
    
    filter_primary ::=
        path "==" literal |
        path "!=" literal
    
    path ::=
        name { "." name }
    
    name ::=
        regex [A-Za-z0-9_-]+
    
    literal ::=
        string |
        boolean |
        number |
        "null"

    string ::=
        
    
    value ::=
        "!delivery_latency" |
        path
    
    ```

=== "Примеры"

    Запрос средней задержки доставки хороших событий показа:

    ```
    sum(events.all.exposition.!delivery_latency) / count(events.all.exposition)

    sum exposition !delivery_latency / count exposition
    ```

    Конверсия из показов в клики:

    ```
    count(events.attributed.click) / count(events.all.exposition)

    count attributed click / count exposition
    ```
    
    p95 задержки доставки всех событий с iOS устройств

    ```
    p95(events.all.*[device.platform == "iOS"].!delivery_latency)

    p95 !delivery_latency where device.platfrom == "iOS"
    ```

    Доля ошибок с браузеров
    
    ```
    count(discarded.all.*[client == "web"]) / count(events.all.*[client == "web"])
    
    count discarded * where client == "web" / count * where client == "web"
    ```

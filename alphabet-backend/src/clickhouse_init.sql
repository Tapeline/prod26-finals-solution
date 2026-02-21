CREATE TABLE IF NOT EXISTS events (
    id String,
    decision_id String,
    experiment_id String,
    flag_key String,
    subject_id String,
    event_type String,
    variant_id String,
    issued_at DateTime64(3),
    received_at DateTime64(3),
    attributes String,
    status LowCardinality(String),
    wants_event_type Nullable(String)
) ENGINE = ReplacingMergeTree()
ORDER BY (event_type, decision_id, id);

CREATE TABLE IF NOT EXISTS discarded_events (
    id String,
    decision_id String,
    experiment_id String,
    flag_key String,
    subject_id String,
    event_type_id String,
    issued_at DateTime64(3),
    received_at DateTime64(3),
    attributes String,
    discard_reason String
) ENGINE = MergeTree()
ORDER BY (event_type_id, decision_id, id);

CREATE TABLE IF NOT EXISTS duplicate_events (
    id String,
    decision_id String,
    experiment_id String,
    flag_key String,
    subject_id String,
    event_type String,
    variant_id String,
    issued_at DateTime64(3),
    received_at DateTime64(3),
    attributes String,
    status LowCardinality(String),
    wants_event_type Nullable(String)
) ENGINE = MergeTree()
ORDER BY (event_type, decision_id, id);

CREATE TABLE IF NOT EXISTS conflict_resolutions (
    timestamp DateTime CODEC(Delta, ZSTD(1)),
    domain String CODEC(ZSTD(1)),
    experiment_id String CODEC(ZSTD(1)),
    policy String CODEC(ZSTD(1)),
    was_applied UInt8
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (domain, experiment_id, timestamp);

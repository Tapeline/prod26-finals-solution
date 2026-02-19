import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from alphabet.metrics.infrastructure.dsl import ClickHouseDSLCompiler
from alphabet.metrics.domain.metrics import Metric, MetricKey
from alphabet.shared.commons import MaybeMissing, MISSING
from alphabet.shared.uuid import generate_uuid

from clickhouse_connect.driver import AsyncClient


@dataclass
class TestEvent:
    id: str
    decision_id: str
    experiment_id: str
    flag_key: str
    subject_id: str
    event_type: str
    variant_id: str
    issued_at: datetime
    received_at: datetime
    attributes: dict[str, Any]
    status: str
    wants_event_type: str | None
    discard_reason: str | None = None


def waiting_evt(
    event_type: str,
    decision_id: str,
    attributes: dict[str, Any] | MaybeMissing = MISSING,
    *,
    wants: str,
    delivery_latency_ms: int = 1,
    eid: str | MaybeMissing = MISSING,
) -> TestEvent:
    exp_id, flag_key, subject_id, variant = decision_id.split(":", maxsplit=3)
    if eid is MISSING:
        eid = generate_uuid()
    if attributes is MISSING:
        attributes = {}
    return TestEvent(
        event_type=event_type,
        decision_id=decision_id,
        experiment_id=exp_id,
        flag_key=flag_key,
        subject_id=subject_id,
        issued_at=datetime.now() - timedelta(milliseconds=delivery_latency_ms),
        received_at=datetime.now(),
        id=eid,
        attributes=attributes,
        status="waiting_attribution",
        wants_event_type=wants,
        variant_id=variant,
    )


def ok_evt(
    event_type: str,
    decision_id: str,
    attributes: dict[str, Any] | MaybeMissing = MISSING,
    delivery_latency_ms: int = 1,
    eid: str | MaybeMissing = MISSING,
) -> TestEvent:
    exp_id, flag_key, subject_id, variant = decision_id.split(":", maxsplit=3)
    if eid is MISSING:
        eid = generate_uuid()
    if attributes is MISSING:
        attributes = {}
    return TestEvent(
        event_type=event_type,
        decision_id=decision_id,
        experiment_id=exp_id,
        flag_key=flag_key,
        subject_id=subject_id,
        issued_at=datetime.now() - timedelta(milliseconds=delivery_latency_ms),
        received_at=datetime.now(),
        id=eid,
        attributes=attributes,
        status="accepted",
        wants_event_type=None,
        variant_id=variant,
    )


def err_evt(
    event_type: str,
    decision_id: str,
    attributes: dict[str, Any] | MaybeMissing = MISSING,
    *,
    reason: str,
    delivery_latency_ms: int = 1,
    eid: str | MaybeMissing = MISSING,
) -> TestEvent:
    exp_id, flag_key, subject_id, variant = decision_id.split(":", maxsplit=3)
    if eid is MISSING:
        eid = generate_uuid()
    if attributes is MISSING:
        attributes = {}
    return TestEvent(
        event_type=event_type,
        decision_id=decision_id,
        experiment_id=exp_id,
        flag_key=flag_key,
        subject_id=subject_id,
        issued_at=datetime.now() - timedelta(milliseconds=delivery_latency_ms),
        received_at=datetime.now(),
        id=eid,
        attributes=attributes,
        status="accepted",
        wants_event_type=None,
        variant_id=variant,
        discard_reason=reason,
    )


async def insert_events(
    client: AsyncClient,
    *events: TestEvent,
    table: str = "events",
):
    data = []
    if table == "discarded_events":
        for e in events:
            row = [
                str(e.id),
                e.decision_id,
                e.experiment_id,
                e.flag_key,
                e.subject_id,
                e.event_type,
                e.issued_at,
                e.received_at,
                json.dumps(e.attributes),
                e.discard_reason,
            ]
            data.append(row)
        cols = [
            "id",
            "decision_id",
            "experiment_id",
            "flag_key",
            "subject_id",
            "event_type_id",
            "issued_at",
            "received_at",
            "attributes",
            "discard_reason",
        ]
    else:
        for e in events:
            row = [
                str(e.id),
                e.decision_id,
                e.experiment_id,
                e.flag_key,
                e.subject_id,
                e.event_type,
                e.variant_id,
                e.issued_at,
                e.received_at,
                json.dumps(e.attributes),
                e.status,
                e.wants_event_type if e.wants_event_type else None,
            ]
            data.append(row)
        cols = [
            "id",
            "decision_id",
            "experiment_id",
            "flag_key",
            "subject_id",
            "event_type",
            "variant_id",
            "issued_at",
            "received_at",
            "attributes",
            "status",
            "wants_event_type",
        ]
    await client.insert(table=table, data=data, column_names=cols)


def compile_dsl(dsl: str):
    return ClickHouseDSLCompiler().compile_dsl(dsl)


def a_metric(key: str, dsl: str) -> Metric:
    return Metric(MetricKey(key), dsl, compile_dsl(dsl))


def now_window(
    forward_backward_delta: timedelta = timedelta(days=1),
) -> tuple[datetime, datetime]:
    now = datetime.now()
    return now - forward_backward_delta, now + forward_backward_delta

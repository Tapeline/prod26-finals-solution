import pytest

from alphabet.metrics.application.interfaces import MetricEvaluationResult
from alphabet.metrics.domain.metrics import Metric, MetricKey
from tests.integration.metric_dsl.helper import (
    insert_events,
    ok_evt,
    a_metric,
    now_window,
    waiting_evt,
    err_evt,
)


@pytest.mark.asyncio
async def test_good_events_selected(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        ok_evt("shown", "e1:flag1:u1:v1"),
        ok_evt("shown", "e1:flag1:u1:v2"),
        ok_evt("shown", "e1:flag1:u1:v2"),
    )
    result = await evaluator.evaluate_for_experiment(
        "e1",
        {"v1": "A", "v2": "B"},
        [a_metric("Exposition", "count shown")],
        *now_window(),
    )
    assert result == {
        MetricKey("Exposition"): MetricEvaluationResult(
            overall=3,
            per_variant={"A": 1, "B": 2},
        ),
    }


@pytest.mark.asyncio
async def test_simple_count_metric(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        ok_evt("click", "e1:f1:u1:v1"),
        ok_evt("click", "e1:f1:u2:v1"),
        ok_evt("click", "e1:f1:u3:v2"),
        ok_evt("view", "e1:f1:u1:v1"),
    )

    result = await evaluator.evaluate_for_experiment(
        "e1",
        {"v1": "A", "v2": "B"},
        [a_metric("Clicks", "count click")],
        *now_window(),
    )

    assert result[MetricKey("Clicks")].per_variant == {"A": 2.0, "B": 1.0}
    assert result[MetricKey("Clicks")].overall == 3.0


@pytest.mark.asyncio
async def test_attributed_arent_counted_twice(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        waiting_evt("click", "e1:f1:u1:v1", eid="1", wants="exposition"),
        ok_evt("click", "e1:f1:u1:v1", eid="1"),
        # actually a single event
    )

    result = await evaluator.evaluate_for_experiment(
        "e1", {"v1": "A"}, [a_metric("Clicks", "count click")], *now_window()
    )

    assert result[MetricKey("Clicks")].overall == 1.0


@pytest.mark.asyncio
async def test_sum_with_json_filters(clickhouse_client, evaluator):
    # Тест: Сумма по полю с фильтром where
    await insert_events(
        clickhouse_client,
        ok_evt("purchase", "e2:f1:u1:v1", {"amount": 100, "currency": "USD"}),
        ok_evt("purchase", "e2:f1:u1:v1", {"amount": 50, "currency": "EUR"}),
        ok_evt("purchase", "e2:f1:u2:v2", {"amount": 20, "currency": "USD"}),
    )

    result = await evaluator.evaluate_for_experiment(
        "e2",
        {"v1": "A", "v2": "B"},
        [
            a_metric(
                "RevenueUSD", 'sum purchase amount where currency == "USD"'
            )
        ],
        *now_window(),
    )

    assert result[MetricKey("RevenueUSD")].per_variant == {
        "A": 100.0,
        "B": 20.0,
    }


@pytest.mark.asyncio
async def test_conversion_ratio(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        # A: 2 views, 1 click -> 50%
        ok_evt("view", "e3:f1:u1:v1"),
        ok_evt("view", "e3:f1:u2:v1"),
        ok_evt("click", "e3:f1:u1:v1"),
        # B: 1 view, 0 clicks -> 0%
        ok_evt("view", "e3:f1:u3:v2"),
    )

    result = await evaluator.evaluate_for_experiment(
        "e3",
        {"v1": "A", "v2": "B"},
        [a_metric("CTR", "count click / count view")],
        *now_window(),
    )

    assert result[MetricKey("CTR")].per_variant == {"A": 0.5, "B": 0.0}
    assert result[MetricKey("CTR")].overall == 1 / 3  # 0.333...


@pytest.mark.asyncio
async def test_attribution_status_filtering(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        ok_evt("buy", "e4:f1:u1:v1"),
        waiting_evt("buy", "e4:f1:u2:v1", wants="some_other_event"),
        # should not be attributed
    )

    result = await evaluator.evaluate_for_experiment(
        "e4",
        {"v1": "A"},
        [
            a_metric("Attr", "count attributed buy"),
            a_metric("Glob", "count buy"),
        ],
        *now_window(),
    )

    assert result[MetricKey("Attr")].per_variant["A"] == 1.0
    assert result[MetricKey("Glob")].per_variant["A"] == 2.0


@pytest.mark.asyncio
async def test_system_latency_metric(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        ok_evt("api", "e5:f1:u1:v1", delivery_latency_ms=100),
        ok_evt("api", "e5:f1:u2:v1", delivery_latency_ms=200),
        ok_evt("api", "e5:f1:u3:v1", delivery_latency_ms=300),
    )

    result = await evaluator.evaluate_for_experiment(
        "e5",
        {"v1": "A"},
        [a_metric("LatP95", "p95 api :delivery_latency")],
        *now_window(),
    )

    val = result[MetricKey("LatP95")].per_variant["A"]
    assert 290 <= val <= 300


@pytest.mark.asyncio
async def test_cross_source_metric(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        ok_evt("view", "e6:f1:u1:v1"),
    )
    await insert_events(
        clickhouse_client,
        err_evt("view", "e6:f1:u2:-", reason="something happened"),
        table="discarded_events",
    )

    metrics = [a_metric("ErrorRate", "count discarded view / count view")]
    print(metrics)

    result = await evaluator.evaluate_for_experiment(
        "e6", {"v1": "A"}, metrics, *now_window()
    )

    assert result[MetricKey("ErrorRate")].overall == 1.0


@pytest.mark.asyncio
async def test_advertised_example_with_ios(clickhouse_client, evaluator):
    await insert_events(
        clickhouse_client,
        ok_evt(
            "abc",
            "e5:f1:u1:v1",
            delivery_latency_ms=100,
            attributes={"device": {"platform": "iOS"}},
        ),
        ok_evt(
            "def",
            "e5:f1:u2:v1",
            delivery_latency_ms=200,
            attributes={"device": {"platform": "iOS"}},
        ),
        ok_evt(
            "ghi",
            "e5:f1:u3:v1",
            delivery_latency_ms=300,
            attributes={"device": {"platform": "symbian"}},
        ),
    )

    result = await evaluator.evaluate_for_experiment(
        "e5",
        {"v1": "A"},
        [
            a_metric(
                "MaxIOSLatency",
                'max * :delivery_latency where device.platform == "iOS"',
            )
        ],
        *now_window(),
    )

    assert result[MetricKey("MaxIOSLatency")].overall == 200

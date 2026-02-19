import pytest
from clickhouse_connect import get_async_client

from alphabet.metrics.infrastructure.evaluator import ClickHouseMetricEvaluator
from tests.integration.config import config


@pytest.fixture(scope="function")
async def clickhouse_client():
    client = await get_async_client(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        database=config.clickhouse.database,
        username=config.clickhouse.username,
        password=config.clickhouse.password,
    )
    yield client
    await client.close()


@pytest.fixture(scope="function", autouse=True)
async def clean_db(clickhouse_client):
    await clickhouse_client.command("TRUNCATE TABLE events")
    await clickhouse_client.command("TRUNCATE TABLE discarded_events")
    await clickhouse_client.command("TRUNCATE TABLE duplicate_events")


@pytest.fixture(scope="function")
async def evaluator(clickhouse_client):
    return ClickHouseMetricEvaluator(clickhouse_client)

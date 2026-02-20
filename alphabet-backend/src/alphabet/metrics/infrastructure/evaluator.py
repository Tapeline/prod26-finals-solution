import logging
from datetime import datetime
from typing import final, override

from clickhouse_connect.driver import AsyncClient

from alphabet.metrics.application.interfaces import (
    MetricEvaluationResult,
    MetricEvaluator,
)
from alphabet.metrics.domain.metrics import Metric, MetricKey, SQLFragment

logger = logging.getLogger(__name__)


@final
class ClickHouseMetricEvaluator(MetricEvaluator):
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    @override
    async def evaluate_for_experiment(
        self,
        experiment_id: str,
        variants: dict[str, str],
        metrics: list[Metric],
        start_at: datetime,
        end_at: datetime,
    ) -> dict[MetricKey, MetricEvaluationResult]:
        results: dict[MetricKey, MetricEvaluationResult] = {}
        for metric in metrics:
            num_fragment, denom_fragment = metric.compiled_expression
            num_data = await self._fetch_aggregated_data(
                num_fragment,
                experiment_id,
                start_at,
                end_at,
            )
            denominator_data = None
            if denom_fragment:
                denominator_data = await self._fetch_aggregated_data(
                    denom_fragment,
                    experiment_id,
                    start_at,
                    end_at,
                )
            results[metric.key] = self._calculate_result(
                num_data,
                denominator_data,
                variants,
            )
        return results

    async def _fetch_aggregated_data_from_discarded(
        self,
        fragment: SQLFragment,
        experiment_id: str,
        start_at: datetime,
        end_at: datetime,
    ) -> dict[str, float]:
        data = {}
        try:
            overall_query = f"""
                SELECT {fragment.select}
                FROM discarded_events
                WHERE experiment_id = %(exp_id)s
                  AND issued_at >= %(start)s
                  AND issued_at < %(end)s
                AND ({fragment.where})
            """  # noqa: S608
            # this is safe, no injection can occur
            params = {
                "exp_id": experiment_id,
                "start": start_at,
                "end": end_at,
            }
            overall_res = await self.client.query(
                overall_query,
                parameters=params,
            )
            if (
                overall_res.result_rows
                and overall_res.result_rows[0][0] is not None
            ):
                data["_overall"] = float(overall_res.result_rows[0][0])
            else:
                data["_overall"] = 0.0
        except Exception as e:
            logger.exception("Error fetching metric part", exc_info=e)
            return {"_overall": 0.0}
        else:
            return data

    async def _fetch_aggregated_data(
        self,
        fragment: SQLFragment,
        experiment_id: str,
        start_at: datetime,
        end_at: datetime,
        /,
    ) -> dict[str, float]:
        table = fragment.table or "events"
        if table == "events":
            table = "events FINAL"
        if table == "discarded_events":
            return await self._fetch_aggregated_data_from_discarded(
                fragment,
                experiment_id,
                start_at,
                end_at,
            )
        query = f"""
            SELECT
                variant_id,
                {fragment.select} as val
            FROM {table}
            WHERE experiment_id = %(exp_id)s
              AND issued_at >= %(start)s
              AND issued_at < %(end)s
              AND ({fragment.where})
            GROUP BY variant_id
            WITH TOTALS
        """  # noqa: S608
        # this is safe, no injection can occur
        params = {"exp_id": experiment_id, "start": start_at, "end": end_at}
        try:
            result = await self.client.query(query, parameters=params)
            data = {}
            for row in result.result_rows:
                variant, val = row
                if variant:
                    data[variant] = float(val) if val is not None else 0.0
            overall_query = f"""
                SELECT {fragment.select}
                FROM {table}
                WHERE experiment_id = %(exp_id)s
                  AND issued_at >= %(start)s
                  AND issued_at < %(end)s
                  AND ({fragment.where})
            """  # noqa: S608
            # this is safe, no injection can occur
            overall_res = await self.client.query(
                overall_query,
                parameters=params,
            )
            if (
                overall_res.result_rows
                and overall_res.result_rows[0][0] is not None
            ):
                data["_overall"] = float(overall_res.result_rows[0][0])
            else:
                data["_overall"] = 0.0
        except Exception as e:
            logger.exception("Error fetching metric part", exc_info=e)
            return {"_overall": 0.0}
        else:
            return data

    async def _fetch_only_overall_data(
        self,
        fragment: SQLFragment,
        experiment_id: str,
        start_at: datetime,
        end_at: datetime,
        /,
    ) -> float | None:
        table = fragment.table or "events"
        if table == "events":
            table = "events FINAL"
        if table == "discarded_events":
            return (
                await self._fetch_aggregated_data_from_discarded(
                    fragment,
                    experiment_id,
                    start_at,
                    end_at,
                )
            ).get("_overall")
        try:
            params = {
                "exp_id": experiment_id,
                "start": start_at,
                "end": end_at,
            }
            overall_query = f"""
                SELECT {fragment.select}
                FROM {table}
                WHERE experiment_id = %(exp_id)s
                  AND issued_at >= %(start)s
                  AND issued_at < %(end)s
                  AND ({fragment.where})
            """  # noqa: S608
            # this is safe, no injection can occur
            overall_res = await self.client.query(
                overall_query,
                parameters=params,
            )
            if (
                overall_res.result_rows
                and overall_res.result_rows[0][0] is not None
            ):
                return float(overall_res.result_rows[0][0])
        except Exception as e:
            logger.exception("Error fetching metric part", exc_info=e)
            return 0.0
        else:
            return 0.0

    def _calculate_result(
        self,
        num_data: dict[str, float],
        denom_data: dict[str, float] | None,
        variants: dict[str, str],
    ) -> MetricEvaluationResult:
        overall_val = num_data.get("_overall", 0.0)
        if denom_data:
            overall_denom = denom_data.get("_overall", 0.0)
            overall_res = _safe_div(overall_val, overall_denom)
        else:
            overall_res = overall_val
        per_variant = {}
        for v_val, v_name in variants.items():
            n_val = num_data.get(v_val, 0.0)
            if denom_data:
                d_val = denom_data.get(v_val, 0.0)
                res = _safe_div(n_val, d_val)
            else:
                res = n_val
            per_variant[v_name] = res
        return MetricEvaluationResult(
            overall=overall_res,
            per_variant=per_variant,
        )

    @override
    async def evaluate_only_overall_for_experiment(
        self,
        experiment_id: str,
        metrics: list[Metric],
        start_at: datetime,
        end_at: datetime,
    ) -> dict[MetricKey, float | None]:
        results: dict[MetricKey, float | None] = {}
        for metric in metrics:
            num_fragment, denom_fragment = metric.compiled_expression
            num_data = await self._fetch_only_overall_data(
                num_fragment,
                experiment_id,
                start_at,
                end_at,
            )
            denominator_data = None
            if denom_fragment:
                denominator_data = await self._fetch_only_overall_data(
                    denom_fragment,
                    experiment_id,
                    start_at,
                    end_at,
                )
            if num_data is None:
                results[metric.key] = None
            elif denominator_data is None:
                results[metric.key] = num_data
            elif denominator_data == 0:
                results[metric.key] = None
            else:
                results[metric.key] = num_data / denominator_data
        return results


def _safe_div(n: int | float, d: int | float) -> float | None:
    return n / d if d and d != 0 else None

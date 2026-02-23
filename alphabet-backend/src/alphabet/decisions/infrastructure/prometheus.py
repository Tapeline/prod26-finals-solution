from typing import final, override

from prometheus_client import Counter

from alphabet.decisions.application import DecisionTelemetry


@final
class PrometheusDecisionTelemetry(DecisionTelemetry):
    def __init__(self) -> None:
        self.counter = Counter(
            "newly_made_decision_count",
            "Newly made decision count",
        )

    @override
    def inc_made_decisions(self, delta: int) -> None:
        self.counter.inc(delta)

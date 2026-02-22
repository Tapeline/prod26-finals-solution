from typing import final, override

from prometheus_client import Counter

from alphabet.subject_events.application.interfaces import EventTelemetry


@final
class PrometheusEventTelemetry(EventTelemetry):
    def __init__(self) -> None:
        self.counter = Counter(
            "processed_events_count",
            "Processed events count",
        )

    @override
    def inc_processed_events(self, delta: int) -> None:
        self.counter.inc(delta)

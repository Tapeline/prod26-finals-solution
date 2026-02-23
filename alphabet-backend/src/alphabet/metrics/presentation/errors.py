from types import MappingProxyType
from typing import Final

from alphabet.metrics.application.exceptions import (
    ExperimentForReportNotFound,
)
from alphabet.metrics.domain.dsl.exceptions import InvalidMetricDSLExpression
from alphabet.metrics.domain.exceptions import (
    InvalidMetricKey,
    InvalidReportWindow,
    MetricAlreadyExists,
    NoSuchMetric,
    NoSuchReport,
)
from alphabet.shared.presentation.framework.errors import infer_code

metrics_err_handlers: Final = MappingProxyType(
    {
        InvalidMetricDSLExpression: (400, infer_code),
        MetricAlreadyExists: (409, infer_code),
        NoSuchMetric: (404, infer_code),
        NoSuchReport: (404, infer_code),
        InvalidReportWindow: (400, infer_code),
        ExperimentForReportNotFound: (404, infer_code),
        InvalidMetricKey: (400, infer_code),
    },
)

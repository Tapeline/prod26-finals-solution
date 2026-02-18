from types import MappingProxyType
from typing import Final

from alphabet.shared.presentation.framework.errors import infer_code
from alphabet.subject_events.application.exceptions import (
    EventTypeAlreadyExists,
    EventTypeNotFound,
)
from alphabet.subject_events.domain.exceptions import (
    InvalidEventTypeId,
    InvalidJsonSchema,
)

subject_events_err_handlers: Final = MappingProxyType(
    {
        EventTypeNotFound: (404, infer_code),
        EventTypeAlreadyExists: (409, infer_code),
        InvalidEventTypeId: (400, infer_code),
        InvalidJsonSchema: (400, infer_code),
    },
)

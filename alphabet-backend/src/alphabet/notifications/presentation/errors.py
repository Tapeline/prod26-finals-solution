from types import MappingProxyType
from typing import Final

from alphabet.notifications.application.exceptions import (
    RuleNotFound,
    FailedToSend,
)
from alphabet.notifications.domain.exceptions import (
    InvalidConnectionString,
    InvalidTrigger, InvalidRatelimit,
)
from alphabet.shared.presentation.framework.errors import infer_code

notification_err_handlers: Final = MappingProxyType(
    {
        RuleNotFound: (404, infer_code),
        FailedToSend: (500, infer_code),
        InvalidConnectionString: (400, infer_code),
        InvalidRatelimit: (400, infer_code),
        InvalidTrigger: (400, infer_code),
    }
)

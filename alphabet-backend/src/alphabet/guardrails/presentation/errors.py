from types import MappingProxyType
from typing import Final

from alphabet.guardrails.application.exceptions import GuardRuleNotFound
from alphabet.shared.presentation.framework.errors import (
    gen_handler_mapping,
    infer_code,
)

guardrail_err_handlers: Final = MappingProxyType(
    {
        GuardRuleNotFound: (404, infer_code)
    }
)
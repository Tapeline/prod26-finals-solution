from types import MappingProxyType
from typing import Final

from alphabet.access.application.exceptions import (
    AlreadyActivated,
    CannotSetReviewRulesForNonExperimenter,
    EmailAlreadyRegistered,
    EmailNotRegistered,
    NoSuchApproverGroup,
    UserIsAnonymous,
    UserNotFound,
)
from alphabet.access.domain import InvalidThreshold
from alphabet.shared.domain.exceptions import NotAllowed
from alphabet.shared.presentation.framework.errors import infer_code

access_err_handlers: Final = MappingProxyType(
    {
        EmailAlreadyRegistered: (409, infer_code),
        UserIsAnonymous: (401, infer_code),
        UserNotFound: (404, infer_code),
        EmailNotRegistered: (404, infer_code),
        AlreadyActivated: (409, infer_code),
        NotAllowed: (403, infer_code),
        CannotSetReviewRulesForNonExperimenter: (409, infer_code),
        NoSuchApproverGroup: (404, infer_code),
        InvalidThreshold: (400, infer_code),
    },
)

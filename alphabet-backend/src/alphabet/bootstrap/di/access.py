from dishka import Provider, Scope, provide, provide_all

from alphabet.access.application.interactors import (
    ActivateUser,
    CreateUser,
    ReadReviewRules,
    ReadUserByEmail,
    ReadUserById,
    SetReviewRules,
    UpdateUser,
)
from alphabet.access.application.interfaces import UserRepository
from alphabet.access.infrastructure.repos import SqlUserRepository


class AccessDIProvider(Provider):
    interactors = provide_all(
        CreateUser,
        ActivateUser,
        UpdateUser,
        SetReviewRules,
        ReadReviewRules,
        ReadUserById,
        ReadUserByEmail,
        scope=Scope.REQUEST,
    )
    user_repo = provide(
        SqlUserRepository,
        provides=UserRepository,
        scope=Scope.REQUEST,
    )


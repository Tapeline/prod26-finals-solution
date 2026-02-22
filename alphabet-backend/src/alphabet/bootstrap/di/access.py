from dishka import AnyOf, Provider, Scope, provide, provide_all

from alphabet.access.application.interactors import (
    ActivateUser,
    CreateUser,
    ReadReviewRules,
    ReadUserByEmail,
    ReadUserById,
    SetReviewRules,
    UpdateUser, ReadMe,
)
from alphabet.access.application.interfaces import UserRepository
from alphabet.access.infrastructure.repos import SqlUserRepository
from alphabet.shared.application.user import UserReader
from alphabet.shared.infrastructure.transaction import SqlTransactionManager


class AccessDIProvider(Provider):
    interactors = provide_all(
        CreateUser,
        ActivateUser,
        UpdateUser,
        SetReviewRules,
        ReadReviewRules,
        ReadUserById,
        ReadUserByEmail,
        ReadMe,
        scope=Scope.REQUEST,
    )

    @provide(scope=Scope.REQUEST)
    def provide_user_repo_for_all(
        self,
        tx: SqlTransactionManager,
    ) -> AnyOf[UserRepository, UserReader]:
        return SqlUserRepository(tx)

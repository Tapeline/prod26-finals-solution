from collections.abc import Sequence

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, patch, post, put
from msgspec import Struct

from alphabet.access.application.interactors import (
    ActivateUser,
    CreateUser,
    CreateUserDTO,
    NewReviewRulesDTO,
    ReadMe,
    ReadReviewRules,
    ReadUserByEmail,
    ReadUserById,
    SetReviewRules,
    UpdateUser,
    UpdateUserDTO,
)
from alphabet.access.domain import ApproverGroup
from alphabet.shared.domain.user import Role, User, UserId
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_BAD_REQUEST,
    RESPONSE_NOT_AUTH_AND_FORBIDDEN,
    RESPONSE_NOT_AUTHENTICATED,
    error_spec,
    success_spec,
)
from alphabet.shared.presentation.openapi import security_defs


class CreateUserRequest(Struct):
    email: str
    role: Role


class UpdateUserRequest(Struct):
    email: str | None = None
    role: Role | None = None


class UpdateApproverGroupRequest(Struct):
    approver_ids: list[str]
    threshold: int


class ApproverGroupResponse(Struct):
    approver_ids: list[str]
    threshold: int

    @classmethod
    def from_group(cls, group: ApproverGroup) -> "ApproverGroupResponse":
        return ApproverGroupResponse(
            approver_ids=[str(uid) for uid in group.approvers],
            threshold=group.threshold,
        )


class UserResponse(Struct):
    id: str
    email: str
    iap_id: str | None
    role: Role

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return UserResponse(
            id=user.id,
            email=user.email,
            iap_id=user.iap_id,
            role=user.role,
        )


class AccessController(Controller):
    path = "/api/v1/accounts"
    tags: Sequence[str] | None = ("Access",)
    security = security_defs

    @post(
        path="/create",
        responses={
            201: success_spec("Created.", UserResponse),
            409: error_spec("Email already exists."),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_user(
        self,
        data: CreateUserRequest,
        interactor: FromDishka[CreateUser],
    ) -> UserResponse:
        user = await interactor(CreateUserDTO(data.email, data.role))
        return UserResponse.from_user(user)

    @get(
        path="/activate",
        responses={
            200: success_spec("Activated.", UserResponse),
            409: error_spec("Already activated."),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def activate_user(
        self,
        interactor: FromDishka[ActivateUser],
    ) -> UserResponse:
        user = await interactor()
        return UserResponse.from_user(user)

    @patch(
        path="/user/{user_id:str}",
        responses={
            200: success_spec("User updated.", UserResponse),
            409: error_spec("Already exists."),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def update_user(
        self,
        user_id: str,
        data: UpdateUserRequest,
        interactor: FromDishka[UpdateUser],
    ) -> UserResponse:
        user = await interactor(
            UserId(user_id),
            UpdateUserDTO(data.email, data.role),
        )
        return UserResponse.from_user(user)

    @get(
        path="/user/by-id/{user_id:str}",
        responses={
            200: success_spec("User retrieved.", UserResponse),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def read_user_by_id(
        self,
        user_id: str,
        interactor: FromDishka[ReadUserById],
    ) -> UserResponse:
        user = await interactor(UserId(user_id))
        return UserResponse.from_user(user)

    @get(
        path="/user/by-email",
        responses={
            200: success_spec("User retrieved.", UserResponse),
            **RESPONSE_BAD_REQUEST,
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def read_user_by_email(
        self,
        email: str,
        interactor: FromDishka[ReadUserByEmail],
    ) -> UserResponse:
        user = await interactor(email)
        return UserResponse.from_user(user)

    @put(
        path="/experimenter/{user_id:str}/approver-group",
        responses={
            200: success_spec("User updated.", ApproverGroupResponse),
            **RESPONSE_BAD_REQUEST,
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def update_approver_group(
        self,
        user_id: str,
        data: UpdateApproverGroupRequest,
        interactor: FromDishka[SetReviewRules],
    ) -> ApproverGroupResponse:
        group = await interactor(
            UserId(user_id),
            NewReviewRulesDTO(
                data.threshold,
                [UserId(uid) for uid in data.approver_ids],
            ),
        )
        return ApproverGroupResponse.from_group(group)

    @get(
        path="/experimenter/{user_id:str}/approver-group",
        responses={
            200: success_spec("Group retrieved.", ApproverGroupResponse),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def read_approver_group(
        self,
        user_id: str,
        interactor: FromDishka[ReadReviewRules],
    ) -> ApproverGroupResponse:
        group = await interactor(UserId(user_id))
        return ApproverGroupResponse.from_group(group)

    @get(
        path="/me",
        responses={
            200: success_spec("Profile retrieved.", UserResponse),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def get_me(self, interactor: FromDishka[ReadMe]) -> UserResponse:
        user = await interactor()
        return UserResponse.from_user(user)

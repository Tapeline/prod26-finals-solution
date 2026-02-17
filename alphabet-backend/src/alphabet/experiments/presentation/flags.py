from collections.abc import Sequence
from datetime import datetime

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, patch, post, put
from msgspec import Struct

from alphabet.experiments.application.interactors.flags import (
    CreateFlag,
    CreateFlagDTO,
    ReadAllFlags,
    ReadFlag,
    UpdateFlag,
)
from alphabet.experiments.domain.flags import FeatureFlag, FlagKey, FlagType
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_BAD_REQUEST,
    RESPONSE_FORBIDDEN, RESPONSE_NOT_AUTH_AND_FORBIDDEN,
    RESPONSE_NOT_AUTHENTICATED,
    RESPONSE_NOT_FOUND, error_spec,
    success_spec,
)
from alphabet.shared.presentation.openapi import security_defs


class CreateFlagRequest(Struct):
    key: str
    description: str
    type: FlagType
    default: str


class UpdateFlagRequest(Struct):
    default: str


class FlagResponse(Struct):
    key: str
    description: str
    type: FlagType
    default: str
    author_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_flag(cls, flag: FeatureFlag) -> "FlagResponse":
        return FlagResponse(
            key=flag.key.value,
            description=flag.description,
            type=flag.type,
            author_id=flag.author_id,
            default=flag.default,
            created_at=flag.created_at,
            updated_at=flag.updated_at,
        )


class FlagsController(Controller):
    path = "/api/v1/flags"
    tags: Sequence[str] | None = ("Flags",)
    security = security_defs

    @post(
        path="/create",
        responses={
            201: success_spec("Created.", FlagResponse),
            409: error_spec("Flag already exists."),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_flag(
        self,
        data: CreateFlagRequest,
        interactor: FromDishka[CreateFlag],
    ) -> FlagResponse:
        flag = await interactor(
            CreateFlagDTO(
                key=FlagKey(data.key),
                description=data.description,
                type=data.type,
                default=data.default
            )
        )
        return FlagResponse.from_flag(flag)

    @get(
        path="",
        responses={
            200: success_spec("Retrieved.", list[FlagResponse]),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def get_all_flags(
        self,
        interactor: FromDishka[ReadAllFlags],
        limit: int = 50,
        offset: int = 0,
    ) -> list[FlagResponse]:
        flags = await interactor(Pagination(limit, offset))
        return list(map(FlagResponse.from_flag, flags))

    @get(
        path="/{flag_key:str}",
        responses={
            200: success_spec("Retrieved.", FlagResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def get_one_flag(
        self,
        interactor: FromDishka[ReadFlag],
        flag_key: str
    ) -> FlagResponse:
        flag = await interactor(FlagKey(flag_key))
        return FlagResponse.from_flag(flag)

    @patch(
        path="/{flag_key:str}",
        responses={
            200: success_spec("Updated.", FlagResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
    )
    @inject
    async def update_flag(
        self,
        flag_key: str,
        data: UpdateFlagRequest,
        interactor: FromDishka[UpdateFlag],
    ) -> FlagResponse:
        flag = await interactor(FlagKey(flag_key), data.default)
        return FlagResponse.from_flag(flag)

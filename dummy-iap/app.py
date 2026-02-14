from pathlib import Path
from typing import Annotated, Any

import aiohttp

from litestar import Litestar, get, post, Request, route
from litestar.params import Body
from litestar.response import Template, Redirect, Response
from litestar.template import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.enums import RequestEncodingType
from litestar.static_files.config import StaticFilesConfig
import os
import re
import tomllib
from dataclasses import dataclass


@dataclass
class User:
    user_id: str
    email: str
    password: str


@dataclass
class IAPConfig:
    upstream: str
    secret: str
    exclude_regex: re.Pattern | None


def load_users(filename: str) -> dict[str, User]:
    with open(filename, "rb") as file:
        raw = tomllib.load(file)
        return {
            user_data["email"]: User(
                user_id, user_data["email"], user_data["password"]
            )
            for user_id, user_data in raw["users"].items()
        }


def load_config(filename: str) -> IAPConfig:
    with open(filename, "rb") as file:
        raw = tomllib.load(file)
        exclude_regex = raw["app"].get("exclude", None)
        return IAPConfig(
            upstream=os.environ["IAP_UPSTREAM"],
            secret=os.environ.get("IAP_SECRET", "1234567812345678"),
            exclude_regex=re.compile(exclude_regex) if exclude_regex else None,
        )


config: IAPConfig | None = None
users: dict[str, User] | None = None


@get("/_iap/login")
async def login() -> Template:
    return Template(
        template_name="login_material.html",
        context={"available_users": users.values()}
    )


@dataclass
class LoginRequest:
    email: str
    password: str


@post("/_iap/login")
async def login_action(
    data: Annotated[
        LoginRequest,
        Body(media_type=RequestEncodingType.URL_ENCODED)
    ],
    request: Request[Any, Any, Any],
    next_to: str | None = None,
) -> Response:
    user = users.get(data.email)
    if not user:
        return Template(
            template_name="login_material.html",
            context={
                "invalid_credentials": True,
                "available_users": users.values()
            }
        )
    request.set_session({"user_id": user.user_id, "user_email": user.email})
    if next_to:
        return Redirect(next_to)
    else:
        return Redirect("/")


@get("/_iap/logout")
async def logout(request: Request) -> Redirect:
    request.clear_session()
    return Redirect("/_iap/login")


@get("/_iap/me")
async def profile(request: Request) -> Response:
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email")
    if not user_id or not user_email:
        return Redirect("/_iap/login?next=/_iap/me")
    return Template(
        "iap_account.html",
        context={"user_id": user_id, "user_email": user_email}
    )


@route("/", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"])
async def index_proxy(request: Request) -> Response:
    return await proxy(request, "")


@route("{path:path}", http_method=["GET", "POST", "DELETE", "PATCH", "PUT"])
async def path_proxy(request: Request, path: str | None = None) -> Response:
    return await proxy(request, path)


async def proxy(request: Request, path: str | None = None) -> Response:
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email")

    if config.exclude_regex and not config.exclude_regex.fullmatch(path):
        if not user_id or not user_email:
            return Redirect(f"/_iap/login?next={request.url}")

    url = f"{config.upstream}/{path.removeprefix('/')}"
    if request.url.query:
        url += f"?{request.url.query}"

    proxy_headers = dict(request.headers)
    proxy_headers.pop("host", None)
    proxy_headers.pop("x-user-id", None)
    proxy_headers.pop("x-user-email", None)

    if user_id and user_email:
        proxy_headers["X-User-Id"] = user_id
        proxy_headers["X-User-Email"] = user_email

    body = await request.body()
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.request(
                method=request.method,
                url=url,
                headers=proxy_headers,
                data=body,
                allow_redirects=False
            ) as response
        ):
            data = await response.read()
            return Response(
                data,
                status_code=response.status,
                headers=dict(response.headers)
            )
    except aiohttp.client_exceptions.ClientConnectorError:
        return Response(
            f"Cannot connect to upstream service",
            status_code=502
        )


def create_app():
    global config, users
    config = load_config("config.toml")
    users = load_users("config.toml")
    session_config = CookieBackendConfig(secret=config.secret.encode("utf8"))
    app = Litestar(
        debug=True,
        middleware=[
            session_config.middleware,
        ],
        route_handlers=[
            login,
            login_action,
            logout,
            index_proxy,
            path_proxy,
            profile
        ],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
        static_files_config=[StaticFilesConfig(
            directories=["static"], path="/_iap-static", name="static"
        )]
    )
    return app


if __name__ == "__main__":
    app = create_app()

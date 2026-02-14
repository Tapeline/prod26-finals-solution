from litestar import Litestar, get, Request


@get(path="/unauthorized")
async def unauthorized(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    user_email = request.headers.get("x-user-email")
    if user_id:
        return f"Hello, {user_email}!\nYou have been logged in as #{user_id}"
    else:
        return "Anonymous"


@get(path="/")
async def index(request: Request) -> str:
    user_id = request.headers["x-user-id"]
    user_email = request.headers["x-user-email"]
    return f"Hello, {user_email}!\nYou have been logged in as #{user_id}"


app = Litestar(route_handlers=[index, unauthorized])

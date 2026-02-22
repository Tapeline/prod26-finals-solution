from litestar import get
from litestar.response import Template


@get("/")
async def serve_frontend() -> Template:
    return Template(
        template_name="index.html",
    )

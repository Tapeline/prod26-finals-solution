FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.13-slim
COPY --from=uv /uv /uvx /bin/


# System dependencies

RUN apt-get update && apt-get install -y git


# Build settings

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy


# Dependencies (so they are cached)

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project


# Set up whole project

COPY . .
RUN uv sync --frozen
RUN chmod +x ./start.sh


# Run

CMD ./start.sh

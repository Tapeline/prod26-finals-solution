#!/bin/bash

uv run alembic upgrade head

# This is some smartypants move suggested by Gemini
# Basically, we want coverage to finish writing, so
# we need to gracefully shutdown.

uv run coverage run -p -m alphabet.bootstrap.entrypoints.cli run server &
PID_UVICORN=$!
uv run coverage run -p -m alphabet.bootstrap.entrypoints.cli run attribution_worker &
PID_ATTR=$!
uv run coverage run -p -m alphabet.bootstrap.entrypoints.cli run guardrails_worker &
PID_GUARD=$!
uv run coverage run -p -m alphabet.bootstrap.entrypoints.cli run notifications_worker &
PID_NOTIF=$!

# Here goes some linux magic I don't understand

shutdown() {
    echo "Received SIGTERM => Shutting down gracefully..."
    kill -SIGTERM $PID_UVICORN $PID_ATTR $PID_GUARD $PID_NOTIF
    wait $PID_UVICORN $PID_ATTR $PID_GUARD $PID_NOTIF
    echo "All processes exited. Coverage written."
}
trap shutdown SIGTERM SIGINT
wait $PID_UVICORN $PID_ATTR $PID_GUARD $PID_NOTIF

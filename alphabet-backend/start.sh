uv run alembic upgrade head
uv run uvicorn app:app --host 0.0.0.0 --port 8000 &
uv run python -m alphabet.bootstrap.entrypoints.attribution_worker &
uv run python -m alphabet.bootstrap.entrypoints.guardrails_worker &
uv run python -m alphabet.bootstrap.entrypoints.notifications_worker &
wait

uv run alembic upgrade head
uv run uvicorn app:app --host 0.0.0.0 --port 8000
wait
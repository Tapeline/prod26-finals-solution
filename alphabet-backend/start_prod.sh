uv run alembic upgrade head
uv run alphabet run server &
uv run alphabet run attribution_worker &
uv run alphabet run guardrails_worker &
uv run alphabet run notifications_worker &
wait

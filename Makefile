.PHONY: install demo demo-api api worker frontend test check migrate
install:
	uv sync --locked
	npm ci
migrate:
	mkdir -p .data
	uv run alembic upgrade head
demo: migrate
	DEALWAGGLE_DEMO_MODE=true uv run dealwaggle-demo
demo-api:
	DEALWAGGLE_DEMO_MODE=true uv run uvicorn dealwaggle.main:app --reload --host 127.0.0.1 --port 8000
api:
	uv run uvicorn dealwaggle.main:app --reload --host 127.0.0.1 --port 8000
worker:
	uv run dealwaggle-worker
frontend:
	npm run dev
test:
	uv run pytest -q
check:
	uv run pytest -q
	npm run build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock alembic.ini ./
COPY backend ./backend
COPY database ./database
RUN uv sync --frozen --no-dev && useradd --create-home app
USER app
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "dealwaggle.main:app", "--host", "0.0.0.0", "--port", "8000"]

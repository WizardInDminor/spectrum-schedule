FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /srv/api
ENV UV_COMPILE_BYTECODE=1 UV_NO_DEV=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]

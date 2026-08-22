.PHONY: dev api-dev web-dev test test-api test-web lint lint-api lint-web migrate revision install

install: ## Install all dependencies
	cd api && uv sync
	cd web && npm install

dev: ## Run API and web dev servers together (Ctrl-C stops both)
	$(MAKE) -j2 api-dev web-dev

api-dev:
	cd api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web-dev:
	cd web && npm run dev

test: test-api test-web ## Run all tests

test-api:
	cd api && uv run pytest

test-web:
	cd web && npm run typecheck

lint: lint-api lint-web ## Lint everything

lint-api:
	cd api && uv run ruff check . && uv run ruff format --check .

lint-web:
	cd web && npm run lint && npm run typecheck

migrate: ## Apply migrations
	cd api && uv run alembic upgrade head

revision: ## Autogenerate a migration: make revision m="add events table"
	cd api && uv run alembic revision --autogenerate -m "$(m)"

# Single entry point for the dev loop. Works in Git Bash / WSL / Linux / macOS.

.PHONY: up down lint test test-integration check contracts openapi clients scaffold ci

up:
	docker compose -f infra/compose.yaml up -d

down:
	docker compose -f infra/compose.yaml down

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy libs services
	uv run lint-imports

test:
	uv run pytest -m "not integration and not live" --cov --cov-fail-under=75

test-integration:
	uv run pytest -m integration

check:
	uv run python tools/check_conventions.py
	uv run python tools/check_event_schemas.py
	npx --yes @stoplight/spectral-cli lint "services/*/openapi.json" --ruleset .spectral.yaml || true

contracts:
	uv run python tools/gen_contracts.py

openapi:
	uv run python tools/export_openapi.py

scaffold:
	uv run python tools/scaffold_service.py $(name)

ci: lint test check

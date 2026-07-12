# Single entry point for the dev loop. Works in Git Bash / WSL / Linux / macOS.

.PHONY: up down lint test test-integration check contracts openapi clients scaffold migrate ci

up:
	docker compose -f infra/compose.yaml up -d

down:
	docker compose -f infra/compose.yaml down

# Add new packages here (and in .github/workflows/ci.yml) as they are created.
MYPY_PACKAGES = -p sa_core -p sa_contracts -p sa_observability -p sa_connector_sdk \
	-p sa_persistence -p sa_messaging -p connector_brain -p catalog -p offer -p mcp_gateway -p matching -p price_history -p api_gateway -p sync_orchestrator

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy $(MYPY_PACKAGES)
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

migrate:   # apply a service's migrations, e.g. `make migrate svc=catalog`
	uv run alembic -c services/$(svc)/alembic.ini upgrade head

ci: lint test check

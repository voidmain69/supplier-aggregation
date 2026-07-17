# Single entry point for the dev loop. Works in Git Bash / WSL / Linux / macOS.

.PHONY: up down lint test test-integration check contracts openapi clients scaffold migrate reembed ci \
	ui-install ui-dev ui-lint ui-test ui-build

UI_DIR = apps/curation-ui

up:
	docker compose -f infra/compose.yaml up -d

down:
	docker compose -f infra/compose.yaml down

# Add new packages here (and in .github/workflows/ci.yml) as they are created.
MYPY_PACKAGES = -p sa_core -p sa_contracts -p sa_observability -p sa_connector_sdk \
	-p sa_persistence -p sa_messaging -p connector_brain -p catalog -p offer -p mcp_gateway -p matching -p price_history -p api_gateway -p sync_orchestrator -p search

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
	# Cooldown for npx-resolved deps — keep in sync with .github/workflows/ci.yml.
	# This is the only floating install in the dev loop: npx resolves the whole spectral
	# tree at run time, so a cold cache picks up whatever was published minutes ago.
	# On 2026-07-14 that pulled @asyncapi/specs 6.11.2 (a compromised build, since
	# unpublished) onto a developer machine, where it executed on import.
	# GNU date (Linux/Git Bash) first, BSD date (macOS) as fallback.
	export npm_config_before="$$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
		|| date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)" && \
		npx --yes @stoplight/spectral-cli lint "services/*/openapi.json" --ruleset .spectral.yaml || true

contracts:
	uv run python tools/gen_contracts.py

openapi:
	uv run python tools/export_openapi.py

scaffold:
	uv run python tools/scaffold_service.py $(name)

migrate:   # apply a service's migrations, e.g. `make migrate svc=catalog`
	uv run alembic -c services/$(svc)/alembic.ini upgrade head

reembed:   # re-embed a service's rows in place, e.g. `make reembed svc=search` (svc: search|matching)
	uv run python -m $(svc).reembed

ci: lint test check

# --- curation-ui (frontend; separate pnpm project, not the uv workspace) -------
ui-install:
	cd $(UI_DIR) && pnpm install --frozen-lockfile

ui-dev:
	cd $(UI_DIR) && pnpm dev

ui-lint:
	cd $(UI_DIR) && pnpm lint && pnpm typecheck && pnpm format

ui-test:
	cd $(UI_DIR) && pnpm test

ui-build:
	cd $(UI_DIR) && pnpm build

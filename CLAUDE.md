# CLAUDE.md — Supplier Aggregation Platform

Multi-supplier product aggregation platform: canonical catalog, multi-account offers (prices/stock),
price history, operator-curated product matching (EAN/UPC/RAG), AI-tools-ready APIs (MCP gateway).

**Read first:** [ARCHITECTURE.md](ARCHITECTURE.md). Decisions with rationale: [docs/adr/](docs/adr/).
Docs are written in Ukrainian; all code, identifiers, comments, commits, and docstrings are English.

## Layout

- `libs/` — shared libraries: `core` (ULID, money, errors, outbox), `contracts` (event/API models, generated
  clients), `connector-sdk` (SupplierConnector protocol, rate limiter, test kit), `observability` (OTel bootstrap).
- `services/` — microservices: `connector-brain`, `sync-orchestrator`, `catalog`, `matching`, `offer`,
  `price-history`, `search`, `api-gateway`, `mcp-gateway`. Same internal structure everywhere:
  `src/<pkg>/{api,domain,adapters,events,settings.py}`.
- `contracts/events/*.json` — JSON Schemas of events (source of truth; Pydantic models are generated from them).
- `tools/` — consistency tooling (run in CI; run locally before pushing).
- `infra/compose.yaml` — full local stack (Postgres+Timescale+pgvector, Redpanda, Redis, MinIO, OTel/Grafana).

## Commands

```
make up             # start local infra stack
make lint           # ruff format --check + ruff check + mypy + import-linter
make test           # unit + integration (testcontainers)
make check          # tools/check_conventions.py + tools/check_event_schemas.py + spectral
make contracts      # regenerate Pydantic models from contracts/events + API clients from OpenAPI
make openapi        # export openapi.json for each service (commit the diff)
make scaffold name=<svc>   # create a new service from template
```

All four of `lint`, `test`, `check`, `openapi` must be clean before any commit.

## Hard rules (enforced by CI, do not fight them)

1. A service NEVER imports another service — only `libs/*`. Cross-service = events (writes) or generated
   HTTP client from `libs/contracts/clients` (reads). Never touch another service's DB schema.
2. `domain/` does no I/O and does not import FastAPI/SQLAlchemy. Adapters implement domain protocols.
3. Events: publish only via the transactional outbox (`libs/core/outbox`); consumers must be idempotent.
   Event payloads must validate against `contracts/events/<type>.json`. Schema changes must be
   backward-compatible — additive only; breaking change = new `type` version.
4. Money is `Decimal` + ISO-4217 code, never float. Timestamps are timezone-aware UTC only. IDs are ULIDs.
5. GTIN/EAN/UPC: always normalize via `libs/core/gtin.py` (GTIN-14 + check digit) before comparing or storing.
6. No secrets in code, config files, logs, or DB — supplier credentials live in Vault, DB stores `credentials_ref`.
   Never log SIDs/tokens or account financial terms.
7. Every endpoint: cursor pagination, RFC 9457 problem+json errors with actionable `detail`, LLM-quality
   `description` on every route/param/field, service `tool_manifest.json` kept in sync (see
   [docs/standards/api-guidelines.md](docs/standards/api-guidelines.md)).
8. Supplier specifics stay inside its connector. If catalog/offer code needs a supplier-specific branch,
   the abstraction is wrong — fix the connector or the connector-sdk DTOs instead.
9. Brain API: max 3 req/s per account, session (SID) cached per account, always go through the connector's
   rate-limited client. Raw responses are archived to S3 before normalization.
10. DB migrations: additive in normal PRs (expand-migrate-contract); destructive ones need a dedicated PR.

## Git workflow

- Branches: `main` (protected, release-only) ← `develop` (integration, default for PRs) ← feature branches.
- Feature branches are cut **from `develop`**, named `feat/<scope>-<short-desc>`, `fix/<scope>-<short-desc>`,
  `chore/...`. PR goes back into `develop` (squash merge). Releases: PR `develop` → `main` (merge commit).
- Never commit or push directly to `main` or `develop` — always via PR with green CI.
- **Everything in git is English**: commit messages, branch names, PR titles and descriptions, code review
  comments. Conventional Commits with service scope: `feat(catalog): add gtin collision queue`.
- Hotfixes: branch `hotfix/...` from `main`, PR into `main`, then back-merge `main` → `develop`.

## Conventions

- Python 3.12, uv workspace. `uv run`/`uv sync` only; never bare pip. Line length 100, ruff + mypy strict.
- structlog only, no `print`. Log events with fields: `log.info("offer_price_updated", offer_id=...)`.
- Tests: `test_<unit>__<scenario>__<expected>`; connector tests run on recorded fixtures
  (`tests/fixtures/<supplier>/`), live API tests are marked `@pytest.mark.live` and excluded from CI.
- New service: always `make scaffold` — never hand-copy an existing service.
- When changing an event or API contract: update the schema in `contracts/`, run `make contracts`,
  update producer + all consumers in the same PR, and note it in the PR description.

## Definition of done for a change

lint + test + check green · contracts regenerated if touched · OpenAPI diff committed · telemetry for new
paths (metrics/trace attrs) · service README updated if behavior changed · no TODO without a ticket.

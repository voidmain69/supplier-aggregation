# api-gateway

The single, authenticated **ingress** in front of the platform's internal services. It owns
no data — it authenticates callers, authorizes them by scope, rate-limits per principal, and
forwards to the owning service, exposing one aggregated, AI-ready OpenAPI surface for internal
services and AI agents.

## Auth

`Authorization: Bearer <token>`. The gateway stores only the **SHA-256 hash** of each token
(`API_GATEWAY_PRINCIPALS`, a JSON map `token_hash -> {subject, scopes}`) — no raw credential
is ever in config. In production the principal store is backed by Vault/DB.

### Scopes

| Scope | Grants |
|---|---|
| `catalog:read` | list/get supplier products + canonical products |
| `offers:read` | list offers / best offer |
| `prices:read` | price history + stats |
| `matching:curate` | curation queue/stats/decisions + confirm/reject/create-new/merge |
| `sync:read` | sync-account state + manual trigger |
| `accounts:financial:read` | (reserved) account financial terms |

## Endpoints (all under `/v1`, all scoped + rate-limited)

| Method | Path | Scope | Forwards to |
|---|---|---|---|
| GET | `/products` · `/products/{id}` | `catalog:read` | catalog |
| GET | `/canonical-products` · `/canonical-products/{id}` | `catalog:read` | matching |
| GET | `/products/{id}/offers` · `/products/{id}/best-offer` | `offers:read` | offer |
| GET | `/offers/{id}/price-history` · `.../stats` | `prices:read` | price-history |
| GET | `/curation/queue` · `/curation/stats` · `/curation/decisions` | `matching:curate` | matching |
| POST | `/curation/links/{id}/confirm` · `.../reject` · `.../create-new` | `matching:curate` | matching |
| POST | `/canonical-products/{id}/merge` | `matching:curate` | matching |
| GET | `/sync/accounts` | `sync:read` | sync-orchestrator |
| POST | `/sync/accounts/{id}/trigger` | `sync:read` | sync-orchestrator |

Downstream problem+json errors are relayed unchanged; a downstream outage becomes `502`.

## Run tests

    uv run pytest services/api-gateway

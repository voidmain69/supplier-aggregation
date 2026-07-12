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
| `catalog:read` | list/get supplier products |
| `offers:read` | list offers / best offer |
| `prices:read` | price history + stats |
| `matching:curate` | curation queue + confirm/reject |
| `accounts:financial:read` | (reserved) account financial terms |

## Endpoints (all under `/v1`, all scoped + rate-limited)

| Method | Path | Scope | Forwards to |
|---|---|---|---|
| GET | `/products` · `/products/{id}` | `catalog:read` | catalog |
| GET | `/products/{id}/offers` · `/products/{id}/best-offer` | `offers:read` | offer |
| GET | `/offers/{id}/price-history` · `.../stats` | `prices:read` | price-history |
| GET | `/curation/queue` | `matching:curate` | matching |
| POST | `/curation/links/{id}/confirm` · `.../reject` | `matching:curate` | matching |

Downstream problem+json errors are relayed unchanged; a downstream outage becomes `502`.

## Run tests

    uv run pytest services/api-gateway

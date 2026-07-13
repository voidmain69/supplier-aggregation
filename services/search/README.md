# search

Finds products for people and agents. Owns a **search index** built from supplier product events
and rebuilt canonical cards, and serves **lexical**, **semantic** and **hybrid** search plus exact
lookups by code, articul and GTIN.

Two processes (separate deployments):
- **API** (`search.main:create_app`) — query endpoints under `/v1`.
- **Consumer** (`python -m search.consumer`) — subscribes to `sa.supplier.product` (index each
  discovered product) and `sa.catalog.product` (`catalog.product.updated` → index canonical cards),
  both idempotent (dedupe by event id).

## Search model

**Lexical**: on PostgreSQL a `tsvector` FTS column over name/brand/articul/codes gives ranked
matches (`ts_rank`); SQLite (tests) falls back to a portable tokenized `LIKE` (every token must
appear, AND). A `pg_trgm`/GIN index keeps it fast.

**Semantic**: each document carries an embedding of `brand + name`; a natural-language query is
embedded and matched by cosine nearest-neighbour (pgvector `<=>` on Postgres, computed in Python on
SQLite). The `Embedder` protocol is the seam: the default `HashingEmbedder` is a deterministic,
dependency-free stand-in (keeps CI/tests offline); `TeiEmbedder` (BAAI/bge-m3 via TEI) is enabled by
`SEARCH_EMBEDDER_URL` — swapping the model never touches the schema.

**Learned-sparse (SPLADE)**: an optional third signal — a `sparsevec` column (splade via TEI,
enabled by `SEARCH_SPARSE_EMBEDDER_URL`); unset ⇒ sparse retrieval is simply off.

**Hybrid** ([ADR-0011](../../docs/adr/0011-hybrid-search-rerank.md)): `POST /v1/search/hybrid` runs
retrieve → **RRF-fuse** (lexical + semantic + sparse pools, `k=60`, no score normalization) →
**cross-encoder rerank** (bge-reranker via TEI). `Reranker` is a domain seam; the default
`NoopReranker` keeps the RRF order, so hybrid works without a GPU.

Exact lookups compare identifiers directly; GTIN is normalized to GTIN-14 first.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/search` | Lexical search (body: query, cursor, limit); cursor-paginated |
| POST | `/v1/search/semantic` | Natural-language semantic search; hits carry a cosine score |
| POST | `/v1/search/hybrid` | RRF fusion + cross-encoder rerank (`cost_class: expensive`) |
| POST | `/v1/search/canonical` | Hybrid search over canonical cards; returns canonical ids |
| GET | `/v1/search/by-code/{code}` | Exact match on supplier product code / external id |
| GET | `/v1/search/by-articul/{articul}` | Exact match on articul |
| GET | `/v1/search/by-gtin/{gtin}` | Exact match on GTIN/EAN/UPC (normalized to GTIN-14) |

Errors are `application/problem+json`; every field/param carries an LLM-quality description.

## Events

| Direction | Type | Topic |
|---|---|---|
| in | `supplier.product.discovered` | `sa.supplier.product` |
| in | `catalog.product.updated` | `sa.catalog.product` |

## Configuration

Env prefix `SEARCH_` (see `settings.py`): `db_dsn`, `kafka_bootstrap`, `consumer_group`,
`embedder_url` (dense TEI; unset ⇒ hashing stand-in), `reranker_url` (unset ⇒ `NoopReranker`),
`sparse_embedder_url` (unset ⇒ no sparse retriever).

## Run tests

    uv run pytest services/search

Unit tests run on SQLite (no Docker); the schema/migrations and FTS/vector paths are also verified
on Postgres via testcontainers (`@pytest.mark.integration`). Rerank/sparse default off, so no GPU.

## Re-embed

After a model or vector-width change, re-embed rows in place: `make reembed svc=search`
(`python -m search.reembed`).

## Follow-ups

Expose search through the api-gateway and mcp-gateway; production TEI hosting for the dense/rerank/
sparse models (currently the home GPU node); filters coverage parity across all three retrievers.

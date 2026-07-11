# Supplier Aggregation Platform

Агрегатор товарів багатьох постачальників: канонічний каталог, мультиакаунтні ціни/наявність,
історія цін, курований матчинг (EAN/UPC/RAG), AI-tools-ready API + MCP.

| Документ | Що там |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Повна архітектура: домен, сервіси, події, потоки, дані, NFR, фази |
| [CLAUDE.md](CLAUDE.md) | Правила для AI-агентів розробки |
| [docs/adr/](docs/adr/) | Рішення з обґрунтуванням (монорепо, Kafka, storage, matching, AI-ready) |
| [docs/standards/](docs/standards/) | Код-стайл, API, події, телеметрія, інфраструктура |
| [contracts/](contracts/) | JSON Schema подій і tool-манифестів (source of truth) |
| [tools/](tools/) | Тулзи консистентності: check_conventions, check_event_schemas, scaffold_service |

## Швидкий старт (після появи коду)

```bash
make up        # локальний стек: Postgres(+Timescale+pgvector), Redpanda, Redis, MinIO, Grafana
make scaffold name=<service>
make lint test check
```

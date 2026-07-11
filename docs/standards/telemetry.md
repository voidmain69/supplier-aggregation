# Стандарт телеметрії

Стек: **OpenTelemetry** (SDK у кожному сервісі через `libs/observability`) → OTel Collector →
Prometheus (метрики) + Tempo (трейси) + Loki (логи) → Grafana. У проді бекенди замінні (Datadog/Cloud) —
сервіси знають тільки OTLP endpoint.

## 1. Обов'язковий мінімум кожного сервісу

Все нижче дає `libs/observability.bootstrap(app)` — сервіс не пише телеметрійний код руками:

- **Traces**: auto-instrumentation FastAPI, httpx, SQLAlchemy, aiokafka/FastStream, Redis.
  W3C trace context наскрізно: HTTP headers ↔ CloudEvents `traceparent`.
- **Metrics** (Prometheus-сумісні через OTLP):
  - RED: `http_requests_total`, `http_request_duration_seconds` (histogram), по route/method/status;
  - події: produced/consumed/duration/lag/dlq (див. events.md §5);
  - runtime: event loop lag, DB pool usage, GC.
- **Logs**: structlog JSON у stdout; поля обов'язкові: `timestamp`, `level`, `event`, `service`, `env`,
  `trace_id`, `span_id`. Кореляція логи↔трейси через trace_id.
- `GET /healthz` (liveness, без залежностей), `GET /readyz` (перевірка БД/Kafka), `GET /metrics` не потрібен —
  метрики йдуть push через OTLP.

## 2. Доменні метрики (специфічні, обов'язкові)

| Метрика | Сервіс | Навіщо |
|---|---|---|
| `sync_job_duration_seconds`, `sync_items_processed_total`, `sync_errors_total` (labels: supplier, account, job_type) | конектори | здоров'я синхронізацій |
| `supplier_api_requests_total`, `supplier_api_request_duration`, `supplier_rate_limit_hits_total` | конектори | бюджет rate limit, деградація API постачальника |
| `data_staleness_seconds` (max age останнього успішного синку per supplier/account) | orchestrator | головний SLI свіжості |
| `price_changes_total`, `price_points_written_total` | price-history | обсяг і аномалії (сплеск = підозра на баг конектора) |
| `matching_queue_depth`, `matching_auto_rate`, `matching_decisions_total` (labels: decision) | matching | пропускна здатність курації |
| `search_requests_total` (labels: mode=lexical/semantic/hybrid), `embedding_backlog` | search | навантаження і борг індексації |
| `mcp_tool_calls_total`, `mcp_tool_duration_seconds`, `mcp_tool_errors_total` (labels: tool, client) | mcp-gateway | використання агентами |

## 3. SLO та алерти

| SLI | SLO | Алерт |
|---|---|---|
| Доступність read API (5xx rate) | 99.9% / 30д | burn rate 2h/6h multi-window |
| p95 латентність: пошук / картка / історія | 400 / 150 / 300 мс | p95 > SLO 10 хв |
| Свіжість цін (`data_staleness_seconds`) | ≤ 15 хв | > 30 хв per supplier |
| Sync failures | 0 поспіль ≥ 3 | 3 fail поспіль одного job |
| DLQ | порожня | нові повідомлення за 15 хв |
| Consumer lag | < 5 хв | > 10 хв |
| Matching queue | < 500 pending | > 1000 або зростання 24h |

Алерти — Alertmanager → канал команди; кожен алерт має runbook-посилання (`docs/runbooks/`).

## 4. Правила

- Кардинальність labels під контролем: ніяких product_id/offer_id у labels (тільки в trace/log).
- Секрети та фінансові умови ніколи не потрапляють у логи/трейси (санітайзер у observability lib + тест).
- Семплінг трейсів: 100% помилок, tail-based 10% успішних у проді; 100% у dev/stage.
- Дашборди в Grafana — provisioned as code (`infra/grafana/dashboards/*.json`), зміни через PR.
- Кожен новий сервіс з'являється на overview-дашборді автоматично (по service label) — scaffold це гарантує.

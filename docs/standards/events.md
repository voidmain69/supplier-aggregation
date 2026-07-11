# Стандарт подій (Event-Driven)

## 1. Формат

- **CloudEvents 1.0**, content-type `application/cloudevents+json`.
- Envelope: `contracts/events/_envelope.json`. Обов'язкові поля: `id` (ULID), `source` (`//sa/<service>`),
  `type`, `time`, `dataschema`, `subject` (aggregate id), `data`.
- `type`: `<domain>.<entity>.<past-tense-action>` — дія в минулому часі, бо подія = факт, що вже стався.
  Приклади: `supplier.offer.price-changed`, `matching.link.confirmed`. Команди (майбутнє/імператив) —
  тільки в `sync.*` (`sync.job.requested`) і явно позначені як команди.
- `data` описується JSON Schema (draft 2020-12) у `contracts/events/<type>.json`. Схема — source of truth;
  Pydantic-моделі в `libs/contracts` генеруються з неї (`make contracts`).

## 2. Топіки та партиціювання

- Топік: `sa.<domain>.<entity>` (усі дії однієї сутності в одному топіку — гарантія порядку).
- Key = aggregate id (`offer_id`, `supplier_product_id`) — порядок гарантований лише в межах ключа.
- Партиції: старт 12 для високотрафікових (`sa.supplier.offer`), 3 для решти; retention 14 діб
  (довгострокова пам'ять — у БД сервісів і S3, не в Kafka).
- DLQ: `sa.dlq.<original-topic>`; повідомлення в DLQ зберігає оригінальні headers + `x-failure-reason`, `x-attempts`.

## 3. Еволюція схем

- У межах major-версії — тільки backward-compatible зміни: додавання optional-полів, розширення enum.
- Заборонено: видалення/перейменування полів, зміна типів, звуження enum. Такі зміни = новий `type` з `.v2`.
- CI (`tools/check_event_schemas.py`) валідує схеми і перевіряє сумісність зі схемою з `main`.
- Консюмери зобов'язані ігнорувати невідомі поля (Pydantic `extra="ignore"`).

## 4. Надійність

- **Продюсер**: transactional outbox — запис у таблицю `outbox` в одній транзакції з бізнес-даними;
  relay (спільний код у `libs/core/outbox.py`) публікує і помічає sent. Прямий produce з бізнес-коду заборонений.
- **Консюмер**: ідемпотентність обов'язкова — dedupe по `event.id` (таблиця `processed_events`, TTL 30 діб)
  або природна upsert-семантика. Обробка: 3 ретраї з backoff (1s/10s/60s) → DLQ.
- **Реплей**: `tools/replay_dlq.py` (перепублікація з DLQ) і реплей з S3 raw payload'ів для конекторів.
- Консюмер-групи: `<service>.<purpose>` (напр. `price-history.ingest`). Один consumer group на призначення.

## 5. Спостережуваність подій

- Trace context (W3C traceparent) — у CloudEvents extension `traceparent`; консюмер продовжує trace.
- Метрики обов'язкові: `events_produced_total`, `events_consumed_total`, `event_processing_duration_seconds`,
  `consumer_lag` (по групах), `dlq_messages_total` — усе з labels `topic`, `type`, `service`.
- Алерт: DLQ > 0 нових за 15 хв; lag > threshold 10 хв.

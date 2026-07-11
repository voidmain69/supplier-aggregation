# API Guidelines (REST + AI-Ready)

Стосується всіх HTTP API сервісів. Лінт: `spectral lint` з правилами `.spectral.yaml` у CI.

## 1. Загальні правила REST

- OpenAPI **3.1**, генерується FastAPI; файл експортується в `services/<name>/openapi.json` командою
  `make openapi` і комітиться (diff видно в PR).
- Версіонування: префікс `/v1`; breaking change = нова major версія поруч, стара живе до EOL-дати.
- Ресурси — іменники в множині, kebab-case: `/v1/canonical-products/{id}/offers`.
- Пагінація — **тільки курсорна**: `?cursor=&limit=`; відповідь `{ "items": [...], "next_cursor": "...", "total_estimate": 123 }`.
  Offset-пагінація заборонена (нестабільна під час синків).
- Сортування стабільне й детерміноване (tie-breaker по id завжди).
- Фільтри — явні query-параметри зі схемою, не «магічний» q-синтаксис (крім search DSL у search-service).
- Датчас — ISO 8601 UTC (`2026-07-11T10:00:00Z`); гроші — `{"amount": "1234.5000", "currency": "UAH"}` (string amount).
- Ідемпотентність: усі GET — чисті; mutating endpoints приймають `Idempotency-Key`.

## 2. Помилки — RFC 9457

```json
{
  "type": "https://errors.sa.internal/offer-not-found",
  "title": "Offer not found",
  "status": 404,
  "detail": "Offer 01J... does not exist or is archived. Use GET /v1/offers?supplier_product_id= to list live offers.",
  "instance": "/v1/offers/01J...",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

- `type` — стабільний URI з реєстру помилок (`libs/core/errors.py`), `detail` містить **підказку до дії**
  (агент має зрозуміти, що робити далі).
- `trace_id` — завжди, для крос-посилання з телеметрією.
- 429 завжди з `Retry-After`.

## 3. Аутентифікація та скоупи

- Сервіси/агенти: `Authorization: Bearer <api-key|jwt>`; люди: OIDC через gateway.
- Скоупи: `catalog:read`, `offers:read`, `prices:read`, `accounts:financial:read`, `matching:curate`, `admin`.
  Endpoint декларує скоуп у OpenAPI `security` — spectral перевіряє наявність.

## 4. AI-Ready вимоги (обов'язкові, перевіряються в CI)

Мета: будь-який endpoint має бути придатним як LLM-tool без додаткових пояснень людини.

1. **Описи для LLM**: кожен endpoint, параметр і поле відповіді має `description` з:
   семантикою, одиницями виміру, діапазонами, прикладом, типовими помилками використання.
   Погано: `"category_id — id категорії"`. Добре: `"Internal category ULID. Get it from GET /v1/categories/tree.
   Do NOT pass supplier category ids here — map them via /v1/supplier-categories."`
2. **`tool_manifest.json`** у корені сервісу (схема — `contracts/tool-manifest.schema.json`):

```json
{
  "service": "offer-service",
  "tools": [
    {
      "name": "get_offers",
      "operation_id": "getOffersByCanonicalProduct",
      "when_to_use": "Current prices and availability across all suppliers/accounts for one canonical product.",
      "when_not_to_use": "Historical prices (use price-history-service.get_price_history).",
      "safety": "read_only",
      "cost_class": "cheap",
      "typical_latency_ms": 100
    }
  ]
}
```

3. **Самодостатні відповіді**: коди супроводжуються назвами (`{"stock_id": 121, "name": "Kyiv WH-1"}`),
   enum-значення документовані в схемі, немає «внутрішніх» магічних чисел без розшифровки.
4. **Стабільність**: та сама відповідь на той самий запит (з точністю до свіжості даних); поля не зникають без
   deprecation-циклу (`deprecated: true` + `Sunset` header мінімум за 90 днів).
5. **Обмеження — явні**: ліміти видачі, максимальні діапазони дат в описах параметрів; при перевищенні —
   зрозумілий problem+json, а не мовчазне обрізання.
6. **`GET /.well-known/tool-manifest`** — сервіс віддає свій маніфест; mcp-gateway агрегує їх автоматично.
7. Довгі операції (> 5 c) — асинхронний патерн: `202 + operation_id` → `GET /v1/operations/{id}`.

## 5. Внутрішні клієнти

- Для кожного сервісу генерується типізований Python-клієнт з OpenAPI у `libs/contracts/clients/` (`make clients`).
  Ручні httpx-виклики чужих сервісів заборонені — тільки згенерований клієнт (єдина точка ретраїв, таймаутів, трейсингу).

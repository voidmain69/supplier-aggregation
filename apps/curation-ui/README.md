# curation-ui

Backoffice для операторів-кураторів матчингу: черга зіставлення, порівняння карток side-by-side,
рішення confirm/reject/create-new/merge з аудитом, журнал рішень, дашборд оператора, моніторинг
синхронізацій (з ручним тригером) і перегляд канонічного каталогу. Ходить **тільки** через
`api-gateway` (bearer + скоупи). Повний план — [docs/curation-ui-plan.md](../../docs/curation-ui-plan.md).

## Стек

React 19 · TypeScript strict · Vite · TanStack Router/Query/Table/Virtual · Tailwind CSS v4 · Zustand ·
Vitest + Testing Library. Типи API генеруються з `services/api-gateway/openapi.json`.

## Розробка

```bash
pnpm install
cp .env.example .env.local     # виставити VITE_API_BASE_URL на свій api-gateway
pnpm dev                       # http://localhost:5173
```

Потрібен запущений `api-gateway` з дозволеним CORS-origin цього SPA
(`API_GATEWAY_CORS_ALLOW_ORIGINS`) і bearer-токен зі скоупами `matching:curate` + `sync:read` (плюс
`catalog:read`, `offers:read`, `prices:read` для повного контексту). У `make up` усе піднімається
разом (UI на <http://localhost:8088>, вхід токеном `dev-operator-token` з кореневого `.env.example`).

## Команди

```bash
pnpm dev            # dev-сервер
pnpm build          # tsc -b + vite build (продакшн-бандл у dist/)
pnpm typecheck      # tsc -b (без емісії)
pnpm lint           # eslint (strict-type-checked + react-hooks + jsx-a11y + boundaries)
pnpm test           # vitest
pnpm format         # prettier --check
pnpm generate:api   # регенерувати типи з ../../services/api-gateway/openapi.json
```

Після зміни контракту gateway: `make openapi` у корені → `pnpm generate:api` тут → закомітити діф.

## Структура

Feature-sliced, залежності лише зверху вниз (лінтиться правилом імпортів між шарами):

```
src/
  app/        bootstrap: провайдери, роутер, тема, error boundary
  pages/      сторінки-композиції: login · dashboard · queue · review · canonical · decisions · sync
  features/   сценарії: curation-decision · canonical-merge · commercial-context · sync-trigger · token-auth
  entities/   доменні відображення: supplier-product · canonical-product · curation · decision · offer ·
              price-history · attribute-diff · stats · sync
  shared/     api (згенерований клієнт + fetch-обгортка) · ui (примітиви) · lib · config
```

`shared/api` — **єдина точка HTTP**; сирий `fetch` поза нею заборонений ESLint.

## Хоткеї (робоче місце ревʼю)

`c` підтвердити · `r` відхилити · `→`/`←` наступний/попередній · `Esc` до черги ·
у черзі: `j`/`k` навігація, `Enter` відкрити.

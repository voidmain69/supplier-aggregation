# Curation UI — план створення

**Статус:** MVP реалізовано (Фази 0–3) · 2026-07-13
**Мова документа:** українська. Код, ідентифікатори, коміти, тексти в git — англійська (правило репо).
**Читати разом з:** [ARCHITECTURE.md](../ARCHITECTURE.md) §5.10, [ADR-0004](adr/0004-matching-pipeline.md),
[api-guidelines.md](standards/api-guidelines.md), [telemetry.md](standards/telemetry.md).

> **Реалізовано (2026-07-13):** Фаза 0 — CORS у gateway, проксі `canonical-products`, `X-Operator-Id`
> gateway→matching (з тестами). Фази 1–3 — застосунок `apps/curation-ui` (React 19 + TS strict + Vite +
> TanStack Router/Query + Tailwind v4): логін токеном, черга з фільтрами/хоткеями/префетчем, робоче місце
> ревʼю (diff атрибутів, confirm/reject з оптимістичним оновленням і відкатом), комерційний контекст
> (офери + спарклайн), канонічний каталог. Клієнт генерується з `api-gateway/openapi.json`; lint (strict +
> межі шарів) / typecheck / 15 тестів / build зелені; Dockerfile + nginx + сервіс у `compose.yaml` (порт
> 8088) + CI-джоб `curation-ui`. **Відкладено (v2):** merge/split/create-new, журнал рішень, категорійний
> мапінг, моніторинг синків, OIDC, Sentry-інтеграція (§3.5–3.6, §11 фаза v2).

---

## 1. Мета і скоуп

Backoffice для операторів-кураторів матчингу (ARCHITECTURE §5.10): черга зіставлення товарів,
side-by-side порівняння карток, рішення confirm/reject з аудитом, перегляд канонічного каталогу.
Категорійний мапінг і моніторинг синхронізацій — v2 (бекенд-API для них ще немає, див. §3.6).

Ключовий продуктовий інваріант (ADR-0004): **помилковий мердж дорожчий за пропущений збіг** — UI
має робити відхилення легким, а підтвердження усвідомленим (видимий diff, впевненість, контекст цін).

Головна метрика успіху UI — **пропускна здатність оператора**: рішень/годину при стабільній precision.
Все у дизайні (клавіатура, префетч, мінімум кліків) підпорядковане цій метриці, а на бекенді вона вже
вимірюється як `matching_queue_depth` / `matching_decisions_total` (telemetry.md §2).

## 2. Поточний стан бекенда (факти, перевірено по коду 2026-07-13)

UI ходить **тільки через api-gateway** (bearer + скоупи + rate limit 20 rps/40 burst, per principal).

Доступно через gateway сьогодні:

| Метод і шлях | Скоуп | Повертає |
|---|---|---|
| `GET /v1/curation/queue?cursor=&limit=` | `matching:curate` | `Page[CurationItemOut]` — `supplier_product_id`, `canonical_product_id`, `method`, `confidence`, `status` |
| `POST /v1/curation/links/{supplier_product_id}/confirm` | `matching:curate` | `LinkDecisionOut`; ідемпотентний; 409 якщо лінк уже rejected |
| `POST /v1/curation/links/{supplier_product_id}/reject` | `matching:curate` | `LinkDecisionOut`; ідемпотентний; 409 якщо вже confirmed |
| `GET /v1/products?supplier=&canonical_product_id=&cursor=&limit=` | `catalog:read` | `Page[SupplierProductOut]` (з `attributes`, `gtin`, `articul`, `brand`) |
| `GET /v1/products/{supplier_product_id}` | `catalog:read` | Картка товару постачальника |
| `GET /v1/products/{id}/offers`, `GET /v1/products/{id}/best-offer` | `offers:read` | Офери (ціни — decimal-рядки + ISO-4217) |
| `GET /v1/offers/{offer_id}/price-history[/stats]` | `prices:read` | Історія/статистика цін в UAH |

Конвенції, на які UI спирається: курсорна пагінація `{items, next_cursor, total_estimate}` (курсор —
непрозорий рядок, передається назад як є); помилки — RFC 9457 `application/problem+json` з `type`,
`detail`, `trace_id`; 429 з `Retry-After`; гроші — рядки, дати — ISO 8601 UTC.

**Прогалини, що блокують або обмежують UI (бекенд-передумови, «Фаза 0» у §8):**

1. **CORS відсутній** у gateway — браузерний SPA з іншого origin не працюватиме. Потрібен
   `CORSMiddleware` зі строгим allowlist origin-ів з конфігурації.
2. **OIDC задекларований, але не реалізований**: авторизація — статичний opaque bearer
   (`API_GATEWAY_PRINCIPALS`). MVP працює на виданому оператору токені; OIDC — окремий бекенд-етап.
3. **`GET /v1/canonical-products*` не проксується через gateway** (є лише напряму в matching) —
   треба додати проксі-роути (скоуп `matching:curate` або `catalog:read`).
4. **Черга не містить назв товарів**: щоб намалювати рядок черги, UI мусить дотягувати картки
   поштучно (N+1). Потрібне адитивне збагачення `CurationItemOut` вкладеними знімками
   `supplier_product {name, brand, gtin, articul}` і `canonical_product {title, brand, gtin}` —
   або окремий `expand=products` параметр.
5. **Ідентичність оператора захардкожена** (`decided_by="operator"` в matching): gateway має
   передавати `principal.subject` у matching (заголовок `X-Operator-Id` від gateway, не від клієнта),
   інакше аудит рішень фіктивний.
6. **Немає endpooint-ів** merge / split / create-new / batch-рішень, категорій, статусу синків —
   відповідні екрани йдуть у v2 разом із бекендом.

## 3. Сторінки, наповнення, функціонал

### 3.1 Вхід (`/login`)

- MVP: поле для bearer-токена (зберігається тільки в пам'яті вкладки + `sessionStorage`), перевірка
  запитом `GET /v1/curation/queue?limit=1`; показ suject/скоупів недоступний (немає introspection) —
  показуємо результат перевірки по скоупах фактичними запитами.
- Після появи OIDC: redirect-flow Authorization Code + PKCE, сторінка стає крихітною обгорткою.

### 3.2 Черга курації (`/queue`) — головний екран

Наповнення рядка: назва і бренд товару постачальника → кандидат (назва канонічного) → бейдж
`method` (`gtin_auto`-колізія / `rag_suggested` / `manual`) → бейдж `confidence` (колір за порогами
0.65/0.85) → вік у черзі. Знизу — курсорна пагінація «завантажити ще».

Функціонал:

- Фільтри-табки: усі / RAG-кандидати / GTIN-колізії; клієнтський фільтр по бренду/постачальнику
  (серверних фільтрів у API поки немає — додати у v1.1 адитивно).
- Клік або `Enter` відкриває робоче місце ревʼю (§3.3); `j`/`k` — навігація по списку.
- Лічильник глибини черги (з `total_estimate`, коли бекенд почне його заповнювати; до того — «50+»).
- Порожній стан «Чергу розібрано 🎉» + помилковий стан з `detail` і `trace_id` з problem+json.

### 3.3 Робоче місце ревʼю (`/queue/{supplier_product_id}`) — серце продукту

Триколонковий макет:

| Ліва колонка | Центр | Права колонка |
|---|---|---|
| **Товар постачальника**: назва, бренд, GTIN, артикул (MPN), external_id/code, категорія постачальника, всі `attributes` | **Diff атрибутів**: рядок = атрибут; збіг — зелений, розбіжність — червоний, є лише з одного боку — сірий; GTIN/brand/MPN — закріплені зверху | **Кандидат (канонічний товар)**: title, brand, GTIN + лінковані товари інших постачальників (`GET /v1/products?canonical_product_id=`) |

Під колонками — **комерційний контекст** (згортається): офери товару постачальника
(`/v1/products/{id}/offers`) і best-offer з ціною в UAH; спарклайн історії ціни
(`/v1/offers/{id}/price-history?granularity=day`) — оператор бачить, чи «схожий товар» не відрізняється
ціною в рази (сильний сигнал не-збігу).

Дії (панель знизу, липка):

- **Confirm** (`c`) / **Reject** (`r`) → POST з `Idempotency-Key` (ULID, генерується на клієнті,
  api-guidelines §1) → оптимістичний перехід до наступного елемента черги, мутація у фоні.
- 409 (конфліктне рішення іншого оператора) → нейтральний тост «Лінк уже вирішено: {status}»,
  елемент зникає з черги. 404 → те саме.
- `Esc` — назад до черги; `→`/`←` — наступний/попередній без рішення (skip).
- Причина відхилення — v2 (API не приймає reason; додати адитивно разом із merge/create-new).

### 3.4 Канонічний каталог (`/canonical`)

- Список з пошуком по GTIN (`GET /v1/canonical-products?gtin=` — після проксі у Фазі 0), статусні
  бейджі `draft`/`confirmed`.
- Детальна сторінка `/canonical/{id}`: картка + всі лінковані товари постачальників + агрегований
  блок оферів (по кожному supplier_product — його офери; API оферів по canonical напряму немає).

### 3.5 Журнал рішень (`/decisions`) — v1.1

Потребує адитивного API `GET /v1/curation/decisions?decided_by=&from=` (аудит уже в БД —
`decided_by`, `decided_at` у `product_links`). До появи — прибрано з навігації.

### 3.6 v2 (потребують нового бекенда, у MVP не входять)

- **Merge / split / create-new** канонічних товарів (зараз створення draft — тільки автоматичне).
- **Категорійний мапінг** (SupplierCategory → Category): у catalog немає жодного API категорій.
- **Моніторинг синхронізацій**: дані є лише в метриках/подіях; до появи API — посилання на
  Grafana-дашборд із хедера UI.
- **Дашборд оператора**: рішень/день, середня впевненість підтверджених, глибина черги (тренд).

## 4. Архітектура фронтенда

### 4.1 Стек (рішення)

| Шар | Вибір | Чому |
|---|---|---|
| Мова/збірка | **TypeScript strict + Vite** | Зафіксовано в ARCHITECTURE §5.10 |
| UI-фреймворк | **React 19** | Зафіксовано; React Compiler вмикаємо з першого дня |
| Роутинг | **TanStack Router** | Типізовані роути й search-params (фільтри черги в URL) |
| Серверний стан | **TanStack Query** | Кеш, ретраї, оптимістичні мутації, префетч |
| Клієнтський стан | локальний state + **Zustand** тільки для UI-дрібниць (тема, розкриті панелі) | Redux надлишковий: 95% стану — серверний |
| API-клієнт | **генерація з `services/api-gateway/openapi.json`** (`openapi-typescript` + тонкий fetch-обгортач) | Дзеркало бекенд-правила «ручні httpx-виклики заборонені»; типи не розходяться з контрактом |
| Компоненти | **shadcn/ui** (Radix primitives + Tailwind CSS v4, копіюються в репо) + **TanStack Table/Virtual** | Повний контроль і власність коду, доступність з Radix, без залежності від дизайн-вендора |
| Форми/валідація | **react-hook-form + zod** | Мінімум форм, але однаковий патерн скрізь |
| Тести | **Vitest + Testing Library + MSW**; e2e — **Playwright** | MSW-моки генеруються з того ж openapi.json |
| Пакетний менеджер | **pnpm** (окремий workspace в `apps/curation-ui`, не змішується з uv) | |

### 4.2 Структура (feature-sliced, дзеркалить бекендний поділ api/domain/adapters)

```
apps/curation-ui/
├── package.json  vite.config.ts  tsconfig.json  eslint.config.js  playwright.config.ts
├── src/
│   ├── app/            # bootstrap: providers (Query, Router, Theme, ErrorBoundary), роути
│   ├── pages/          # тонкі сторінки-композиції: queue/, review/, canonical/, login/
│   ├── features/       # сценарії з логікою: curation-decision/, queue-filters/, token-auth/
│   ├── entities/       # доменні відображення: supplier-product/, canonical-product/, offer/,
│   │                   #   price-history/ — картки, бейджі, hooks запитів (useSupplierProduct…)
│   └── shared/
│       ├── api/        # згенерований клієнт, fetch-обгортка (auth, problem+json, traceparent,
│       │               #   Idempotency-Key, retry на 429 з Retry-After), хелпери пагінації
│       ├── ui/         # примітиви shadcn/ui + власні: Money, TimeAgo, ConfidenceBadge,
│       │               #   CursorList, EmptyState, ProblemAlert
│       ├── lib/        # утиліти (hotkeys, ulid, formatters)
│       └── config/     # env (VITE_API_BASE_URL, VITE_SENTRY_DSN), design tokens
└── tests/e2e/
```

Правило залежностей (лінтиться `eslint-plugin-boundaries`): `pages → features → entities → shared`;
нижні шари не імпортують верхні; `shared/api` — єдина точка HTTP (аналог правила про згенеровані
клієнти в libs/contracts).

### 4.3 Правила роботи з API

- Всі запити — через згенерований клієнт; сирий `fetch` поза `shared/api` заборонений (ESLint
  `no-restricted-imports`/`no-restricted-globals`).
- Обгортка централізовано: додає `Authorization`, `traceparent` (W3C, для наскрізного трейсингу
  з бекендом), `Idempotency-Key` на mutating; парсить problem+json у типізований `ApiProblem`
  (з `trace_id`); на 429 чекає `Retry-After` і повторює 1 раз; на 401 — розлогін.
- Пагінація: єдиний hook `useCursorList(queryKey, fetchPage)` поверх `useInfiniteQuery`; курсор —
  чорна скринька, 422 на зіпсутий курсор → перезапит без курсора.
- Ключі кешу — фабрика `queryKeys.ts` (одне місце інвалідації після мутацій).
- Контракт оновлюється так само, як у бекенді: `make openapi` → закомічений diff →
  `pnpm generate:api` (CI перевіряє, що згенероване не розійшлося з openapi.json).

## 5. Перевикористання компонентів

- **Примітиви** (`shared/ui`) — тільки презентаційні, без запитів: Button, Badge, Card, Table,
  Skeleton, Toast, Dialog, Tooltip, Kbd (підказки хоткеїв).
- **Доменні компоненти** (`entities/*`) — один компонент на сутність, використовується всюди, де
  сутність зʼявляється: `SupplierProductCard`, `CanonicalProductCard`, `AttributeDiffTable`,
  `OfferRow`, `PriceSparkline`, `ConfidenceBadge`, `MethodBadge`, `GtinText` (моноширинний,
  copy-to-clipboard). Заборонено дублювати відображення сутності всередині pages/features.
- **Композити** — сторінки складаються з доменних компонентів; якщо шматок потрібен двом сторінкам,
  він опускається в entities/shared, а не копіюється.
- Стани loading/empty/error — стандартизовані обгортки `QueryBoundary` (skeleton → data → `ProblemAlert`),
  щоб кожен екран не вигадував власні.
- Storybook не заводимо на MVP (команда маленька); замість нього — сторінка `/dev/kitchen-sink`
  у dev-збірці з усіма примітивами.

## 6. Безпека

1. **Токени**: тільки памʼять + `sessionStorage` (не `localStorage` — коротший життєвий цикл,
   не шариться між вкладками назавжди). Після OIDC — Authorization Code + PKCE, access-токен у
   памʼяті, silent refresh. Токен ніколи не потрапляє в URL, логи, Sentry (санітайзер beforeSend).
2. **XSS**: дані постачальників (`name`, `attributes`) — **недовірений ввід** (приходять із
   зовнішніх API постачальників). Тільки текстовий рендер React; `dangerouslySetInnerHTML`
   заборонений ESLint-правилом; жодного рендера HTML з даних.
3. **CSP** (віддається веб-сервером статики): `default-src 'self'; connect-src 'self' <gateway>
   <sentry>; frame-ancestors 'none'`; без inline-скриптів (Vite це підтримує).
4. **CORS/gateway**: строгий allowlist origin-ів у gateway (Фаза 0); credentials не використовуємо
   (bearer у заголовку). UI не ходить повз gateway ні в які сервіси.
5. **Авторизація по скоупах**: UI ховає дії, на які немає скоупа (після OIDC скоупи будуть у
   токені; до того — «спробував → 403 → сховали»), але **ніколи не вважає приховування захистом** —
   захист на боці gateway.
6. **Ланцюг постачання**: `pnpm audit` + Dependabot у CI; lockfile комітиться; мінімум залежностей
   (кожна нова — через PR-рев'ю); збірка з `--frozen-lockfile`.
7. **Секрети**: у бандлі немає жодних (тільки публічні `VITE_*` URL/DSN); правило перевіряється
   на CI грепом бандла на патерни ключів.
8. **Аудит**: кожне рішення оператора вже пишеться в БД matching (`decided_by/decided_at`);
   Фаза 0 привʼязує його до реального `principal.subject`.

## 7. Моніторинг помилок і телеметрія

- **Sentry** (SaaS або self-hosted GlitchTip — вирішити при старті; SDK однаковий):
  ErrorBoundary на кожному роуті + глобальний `onunhandledrejection`; release = git SHA,
  source maps заливаються в CI (у прод-бандл не потрапляють); санітайзер прибирає токени й
  фінансові поля з breadcrumbs (та сама вимога, що в telemetry.md §4 для бекенда).
- **Звʼязка з бекенд-трейсами**: fetch-обгортка шле `traceparent`; при помилці API показуємо
  оператору `trace_id` із problem+json («Повідомте trace_id підтримці») і кладемо його в Sentry-тег —
  прямий місток у Tempo/Grafana.
- **Продуктові метрики фронта**: web-vitals (LCP/INP/CLS) → Sentry Performance; кастомні події:
  `curation_decision` (confirm/reject, тривалість ревʼю), `queue_page_loaded`. Це фронтовий
  двійник бекендної `matching_decisions_total`.
- **Алерти**: сплеск JS-помилок (>1% сесій) і сплеск 4xx/5xx від gateway по route — у той самий
  канал команди, що й бекенд-алерти.

## 8. Оптимізація продуктивності

Бюджети (перевіряються в CI через `size-limit` і Lighthouse CI на PR):

| Метрика | Бюджет |
|---|---|
| Initial JS (gzip) | ≤ 250 KB |
| LCP черги (кеш теплий) | ≤ 1.5 c |
| INP (рішення confirm/reject) | ≤ 100 мс |
| Перехід до наступного елемента черги | ≤ 150 мс (за рахунок префетчу) |

Прийоми:

- **Code splitting по роутах** (lazy routes TanStack Router); charts (спарклайн) — окремий чанк.
- **Префетч наступного елемента**: коли оператор відкрив елемент N, у фоні тягнемо картки для N+1
  з черги — перехід після рішення миттєвий. Це найважливіша оптимізація для метрики рішень/годину.
- **Оптимістичні мутації**: confirm/reject не блокують UI; відкат + тост при фейлі.
- **Віртуалізація** довгих списків (TanStack Virtual) — черга і лінковані товари.
- **Кеш-політика Query**: `staleTime` 30 с для черги, 5 хв для карток/канонічних, інвалідація
  точкова по ключах після мутацій; ніяких повних refetch-ів екрана.
- React Compiler замість ручних `memo/useCallback`; профілювання лише при реальних проблемах.
- Rate limit gateway (20 rps) поважаємо: збагачення рядків черги — батчами по видимих рядках
  (IntersectionObserver), а після Фази 0 — взагалі без дозапитів (embedded snapshots).

## 9. Дизайн-система

### 9.1 Токени (CSS variables, світла/темна тема)

- **Колір**: семантичні токени поверх нейтральної шкали — `--bg`, `--surface`, `--border`,
  `--text`, `--text-muted`, `--accent` (дії), `--success` (confirm/збіг), `--danger`
  (reject/розбіжність), `--warning` (GTIN-колізія, низька впевненість), `--info`.
  Компоненти використовують **тільки семантичні токени**, ніколи сирі кольори.
- **Confidence-шкала**: ≥0.85 — success, 0.65–0.85 — warning, <0.65 — danger; та сама шкала
  всюди (бейджі, рядки diff).
- **Типографіка**: Inter (UI), JetBrains Mono (GTIN, артикули, ID, ціни); розміри 12/13/14/16/20/24;
  базовий 14px — це щільний backoffice, не маркетинговий сайт.
- **Сітка/відступи**: шкала 4px (4/8/12/16/24/32); радіуси 6/10; тіні мінімальні (2 рівні).
- **Щільність**: компактні таблиці (row 36px), форми без «повітря» — оператор працює годинами.

### 9.2 Принципи

1. **Keyboard-first**: усі дії ревʼю мають хоткеї (`c`/`r`/`j`/`k`/`Enter`/`Esc`/`→`), видимі
   підказки `<Kbd>`; ціль — ревʼю без миші.
2. **Стани обовʼязкові**: кожен екран має спроєктовані loading (skeleton, не спінер), empty,
   error (з `detail` і `trace_id`) і partial (частина карток не довантажилась) стани.
3. **Доступність — WCAG 2.1 AA**: контраст 4.5:1, фокус-індикатори, aria з Radix, `jsx-a11y`
   в ESLint; колір ніколи не єдиний носій сенсу (бейджі мають текст, diff — іконки).
4. **Мова інтерфейсу — українська**; рядки в `shared/config/i18n.ts` (плоский словник, без
   i18n-фреймворка на MVP — мова одна), у коді — тільки ключі англійською.
5. **Незворотні дії** (у v2: merge, масові операції) — тільки з confirm-діалогом; одиничні
   confirm/reject — без діалога (вони ідемпотентні й виправні повторним рішенням лише частково,
   тому в тості після рішення — посилання «переглянути» на 5 с).

## 10. Правила коду (frontend-доповнення до стандартів репо)

При старті імплементації цей розділ виноситься в `docs/standards/frontend.md`.

- **TypeScript strict**, `noUncheckedIndexedAccess`; `any` заборонений (`@typescript-eslint/no-explicit-any`
  = error); типи API — тільки згенеровані, ручне дублювання типів контракту заборонене.
- **ESLint** (flat config): `typescript-eslint` strict-type-checked + `react-hooks` + `jsx-a11y` +
  `boundaries` (шари §4.2); **Prettier** без обговорень; ширина рядка 100 (як у Python-коді репо).
- **Іменування**: файли й директорії — kebab-case; компоненти — PascalCase named exports
  (default export заборонений, крім lazy-роутів); hooks — `useX`; обробники — `handleX`;
  boolean-пропси — `isX/hasX`.
- Компонент ≤ ~150 рядків — далі декомпозиція; логіка — у hooks, JSX — тонкий.
- **Коментарі, ідентифікатори, коміти — англійською**; коміти — Conventional Commits зі скоупом
  `curation-ui`: `feat(curation-ui): add review workspace hotkeys`.
- **Тести**: іменування `describe(unit) → it("scenario → expected")` (дзеркало бекендного
  `test_<unit>__<scenario>__<expected>`); колокація `*.test.tsx` поруч із кодом; MSW-моки з
  openapi.json — ручні фікстури відповідей заборонені для полів, яких немає в контракті.
  Мінімум на PR: логіка features покрита unit, happy-path сторінки — інтеграційний тест з MSW.
- **E2E** (Playwright): один smoke-сценарій «логін → черга → відкрити → confirm → елемент зник»
  проти локального стека (`make up` + сид-дані) — запускається в CI nightly, не на кожен PR.
- **CI**: новий job `frontend` у `.github/workflows/ci.yml` — `pnpm lint && pnpm typecheck &&
  pnpm test && pnpm build && pnpm size` (path-filter на `apps/curation-ui/**`); Makefile-цілі
  `ui-dev`, `ui-lint`, `ui-test`, `ui-build`.
- **Definition of done** для зміни в UI: lint+typecheck+test зелені · бюджети §8 не перевищені ·
  нові екрани мають усі 4 стани §9.2 · хоткеї задокументовані в `<Kbd>`-підказках · README
  апки оновлений при зміні поведінки.

## 11. Етапи впровадження

| Фаза | Обсяг | Вихід (DoD) |
|---|---|---|
| **0. Бекенд-передумови** (PRs у сервіси, без UI) | CORS у gateway (allowlist з конфігурації); проксі `GET /v1/canonical-products*`; адитивне збагачення `CurationItemOut` знімками товарів; `X-Operator-Id` від gateway → `decided_by` у matching | Контракти в openapi.json оновлені, `make openapi` diff закомічений |
| **1. Каркас** | `apps/curation-ui` (Vite+TS+роутер+Query+shadcn), генерація клієнта, fetch-обгортка (auth/problem+json/traceparent), login, CI job, Dockerfile + запис у `infra/compose.yaml` | `make up` піднімає UI; логін токеном працює; CI зелений |
| **2. Черга + ревʼю (MVP)** | Сторінки §3.2–3.3 без комерційного контексту: черга, diff атрибутів, confirm/reject з оптимістичними мутаціями, хоткеї, префетч N+1 | Оператор реально розбирає чергу; e2e smoke зелений |
| **3. Контекст і каталог** | Комерційний блок (офери, спарклайн history), сторінки canonical (§3.4), збагачені фільтри черги | Повний MVP §3; бюджети §8 у CI |
| **4. Експлуатаційна зрілість** | Sentry + source maps + алерти, web-vitals, Lighthouse CI, kitchen-sink, польові правки UX за відгуками операторів | Дашборд помилок; runbook у `docs/runbooks/curation-ui.md` |
| **v2** | OIDC (gateway + UI), merge/split/create-new, журнал рішень, категорійний мапінг, моніторинг синків, дашборд оператора | Окремі ADR/плани на кожен пункт |

Фази 1–3 — незалежні невеликі PR у `develop` (гілки `feat(curation-ui)/...`), як прийнято в репо.

## 12. Ризики та відкриті питання

| Ризик / питання | Мітигація / рішення потрібне від |
|---|---|
| Rate limit 20 rps на principal спільний для всіх операторів за одним токеном | Фаза 0: окремий principal на оператора; згодом OIDC розвʼязує повністю |
| `total_estimate` ніколи не заповнюється — немає чесної глибини черги в UI | Дешевий count у matching-репозиторії (адитивно) або показ «50+» |
| Черга віддає лише одного найкращого кандидата на товар (top-1, не top-k) | Для MVP достатньо; top-k — зміна API matching у v2 |
| Sentry SaaS vs self-hosted GlitchTip (дані карток ідуть у third-party) | Рішення власника платформи до Фази 4; до того — тільки ErrorBoundary + логи |
| Мова UI лише українська — чи потрібна англійська для агентів/скрінів? | Продуктове рішення; архітектурно словник уже відокремлений |

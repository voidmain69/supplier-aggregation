# Стандарт інфраструктури

## 1. Середовища

| Середовище | Де | Призначення |
|---|---|---|
| **dev** | локально, `make up` (Docker Compose, `infra/compose.yaml`) | повний стек на ноутбуці: Postgres(+Timescale+pgvector), Redpanda, Redis, MinIO, OTel/Grafana |
| **stage** | Kubernetes | інтеграція з реальними API постачальників (окремі тестові акаунти), прогін повних синків |
| **prod** | Kubernetes | бойове |

## 2. Контейнери та деплой

- Кожен сервіс — свій Dockerfile (спільний base image `infra/docker/base.Dockerfile`: python:3.12-slim,
  uv, non-root user, multi-stage). Розмір фінального image < 300 MB.
- Kubernetes: Helm-чарти в `infra/helm/` — один спільний library chart + values per service
  (сервіси однакові за формою, тому один чарт покриває всі).
- Обов'язково для кожного Deployment: resource requests/limits, liveness=`/healthz`, readiness=`/readyz`,
  PodDisruptionBudget, HPA для read-сервісів (CPU+RPS), окремі Deployment для API і консюмерів одного сервісу.
- Деплой: GitHub Actions → build+push image (tag = git sha) → helm upgrade stage (авто) → prod (manual approve).
  Rollback = helm rollback, БД-міграції тому тільки backward-compatible (expand-migrate-contract).
- Міграції: Alembic запускається як init-job перед rollout, ніколи при старті пода.

## 3. Дані

- PostgreSQL: керований кластер (або Patroni), 1 primary + read replica; schema-per-service, окремий DB user
  per service з правами тільки на свою схему. Backup: WAL-G, PITR, добові повні; відновлення тестується щоквартально.
- Kafka/Redpanda: 3 ноди в prod, replication factor 3, `acks=all` для продюсерів.
- Redis: тільки кеш і rate-limit стан — втрата допустима, персистентність вимкнена.
- S3/MinIO: bucket `sa-raw` (raw payload постачальників, lifecycle 180 діб → glacier/delete), `sa-media` (зображення).

## 4. Секрети та безпека

- Секрети: Vault (prod/stage) / SOPS-файл (dev). У k8s — через external-secrets operator. У git — ніколи;
  gitleaks у pre-commit і CI.
- Credentials постачальників: тільки у Vault, шлях `sa/suppliers/<supplier>/<account>`; сервіси отримують
  за коротким TTL. У БД SupplierAccount — лише `credentials_ref`.
- Мережа: сервіси не публікуються назовні напряму — тільки api-gateway і mcp-gateway через ingress (TLS, WAF).
  NetworkPolicy: default deny, явні дозволи.
- Образи скануються (trivy) у CI; base image оновлюється щомісяця (renovate).
- Аудит: усі mutating-виклики і рішення операторів → append-only audit log (таблиця + експорт).

## 5. CI (GitHub Actions, `.github/workflows/ci.yml`)

Пайплайн на PR (тільки для змінених пакетів — визначає `tools/changed_packages.py`):

1. `ruff format --check` + `ruff check` + `mypy`
2. `tools/check_conventions.py` (структура сервісів, import rules, tool manifests)
3. `tools/check_event_schemas.py` (валідність + backward compatibility схем подій)
4. `spectral lint` OpenAPI експортів
5. unit tests → integration tests (testcontainers) → coverage gate
6. build docker images (тільки змінені сервіси)

`main`: те саме + push images + deploy stage.

## 6. Вартість/масштаб за замовчуванням

- Старт: 1 нода k8s pool для платформи достатня (усі сервіси легкі, крім embedding-воркера — йому GPU не потрібен
  при API-моделі ембедингів або 1 CPU-ноді для bge-m3).
- Точки масштабування, коли виростемо: search-service (репліки), price-history (Timescale multi-node не знадобиться
  до мільярдів точок), конектори (по акаунтах).

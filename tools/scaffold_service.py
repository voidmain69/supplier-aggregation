"""Scaffold a new service with the mandatory platform structure.

Usage: uv run python tools/scaffold_service.py <service-name>
Example: uv run python tools/scaffold_service.py connector-acme

Creates services/<name>/ with the canonical layout so that check_conventions.py
passes from day one. Never hand-copy an existing service.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PYPROJECT = """\
[project]
name = "{name}"
version = "0.1.0"
description = "TODO: one line — what this service owns"
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "sa-core",
    "sa-contracts",
    "sa-observability",
]

[tool.uv.sources]
sa-core = {{ workspace = true }}
sa-contracts = {{ workspace = true }}
sa-observability = {{ workspace = true }}

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{pkg}"]
"""

MAIN = '''\
"""Application entry point. Wire-up only — no business logic here."""

from fastapi import FastAPI

from {pkg}.settings import Settings


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="{name}",
        version="0.1.0",
        description="TODO: LLM-quality description of what this service does and when to call it.",
    )
    # from sa_observability import bootstrap
    # bootstrap(app, service_name="{name}", settings=settings)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {{"status": "ok"}}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> dict[str, str]:
        # TODO: check DB / broker connectivity
        return {{"status": "ok"}}

    return app
'''

SETTINGS = """\
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="{env_prefix}_")

    otlp_endpoint: str = "http://localhost:4317"
    # db_dsn: str
    # kafka_bootstrap: str = "localhost:19092"
"""

DOCKERFILE = """\
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev --frozen || uv sync --no-dev
COPY src ./src
RUN useradd -m app
USER app
CMD ["uv","run","uvicorn","{pkg}.main:create_app","--factory","--host","0.0.0.0","--port","8000"]
"""

README = """\
# {name}

TODO: what this service owns, which events it consumes/produces, which APIs it exposes.

## Events

| Direction | Type | Topic |
|---|---|---|

## Run tests

    uv run pytest services/{name}
"""


def main() -> int:
    if len(sys.argv) != 2 or not re.match(r"^[a-z][a-z0-9-]+$", sys.argv[1]):
        print(__doc__, file=sys.stderr)
        return 1
    name = sys.argv[1]
    pkg = name.replace("-", "_")
    env_prefix = pkg.upper()
    svc = ROOT / "services" / name
    if svc.exists():
        print(f"services/{name} already exists", file=sys.stderr)
        return 1

    (svc / "src" / pkg / "api").mkdir(parents=True)
    (svc / "src" / pkg / "domain").mkdir()
    (svc / "src" / pkg / "adapters").mkdir()
    (svc / "src" / pkg / "events").mkdir()
    (svc / "tests").mkdir()
    (svc / "migrations").mkdir()

    for sub in ("", "api", "domain", "adapters", "events"):
        (svc / "src" / pkg / sub / "__init__.py").write_text("", encoding="utf-8")
    (svc / "tests" / "__init__.py").write_text("", encoding="utf-8")

    (svc / "pyproject.toml").write_text(PYPROJECT.format(name=name, pkg=pkg), encoding="utf-8")
    (svc / "src" / pkg / "main.py").write_text(MAIN.format(pkg=pkg, name=name), encoding="utf-8")
    (svc / "src" / pkg / "settings.py").write_text(
        SETTINGS.format(env_prefix=env_prefix), encoding="utf-8"
    )
    (svc / "Dockerfile").write_text(DOCKERFILE.format(pkg=pkg), encoding="utf-8")
    (svc / "README.md").write_text(README.format(name=name), encoding="utf-8")
    (svc / "tool_manifest.json").write_text(
        json.dumps({"service": name, "tools": []}, indent=2) + "\n", encoding="utf-8"
    )

    print(f"scaffolded services/{name} (package {pkg})")
    print("next: uv sync && add the service to infra/compose.yaml and CI matrix if needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

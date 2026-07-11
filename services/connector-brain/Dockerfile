FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev --frozen || uv sync --no-dev
COPY src ./src
RUN useradd -m app
USER app
CMD ["uv","run","uvicorn","connector_brain.main:create_app","--factory","--host","0.0.0.0","--port","8000"]

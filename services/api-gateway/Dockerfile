# Built from the repository root as context (uv workspace):
#   docker build -f services/api-gateway/Dockerfile -t api-gateway .
# Compose (infra/compose.yaml) builds it with context: .. and overrides `command`
# for the consumer/relay processes.
FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

# Copy the whole workspace (libs are workspace deps of every service) and install.
COPY pyproject.toml ./
COPY libs ./libs
COPY services ./services
RUN uv sync --all-packages --no-dev

RUN useradd -m app && chown -R app /app
USER app
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api_gateway.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# syntax=docker/dockerfile:1.7
# ---------- etapa 1: dependencias con uv (instalación rápida y cacheada)
FROM python:3.14-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY requirements-api.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && VIRTUAL_ENV=/opt/venv uv pip install -r requirements-api.txt

# ---------- etapa 2: imagen final liviana, usuario sin privilegios
FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app
COPY --from=deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONPATH=/app/src:/app \
    DIR_MODELOS=/app/models DIR_DATOS=/app/data/processed
# Memoria: cada worker de uvicorn carga su propia copia de modelos y panel (~470 MB), así que se usa
# uno solo (WEB_CONCURRENCY); y Polars con 2 hilos reserva ~85 MB menos al leer el panel que con todos.
# Ver README, "Consumo de memoria".
ENV WEB_CONCURRENCY=1 POLARS_MAX_THREADS=2
WORKDIR /app
COPY --chown=app:app src/ src/
COPY --chown=app:app api/ api/
COPY --chown=app:app models/ models/
COPY --chown=app:app data/processed/*.parquet data/processed/
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]

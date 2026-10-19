# Imagen del backend (API) y del entrenamiento del modelo
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# LightGBM necesita la libreria OpenMP (libgomp)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Primero las dependencias: si no cambian, Docker reutiliza esta capa
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY src ./src
COPY api ./api

# Usuario sin privilegios (no correr como root)
RUN useradd --create-home appuser \
    && mkdir -p /app/models \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]

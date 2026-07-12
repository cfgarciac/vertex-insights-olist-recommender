# Dockerfile - API del producto P1 (HU-14, D-39)
#
# La imagen sirve la API FastAPI (src/api/main.py) con el artefacto
# producto_promesa_riesgo.joblib y los lookups de serving.
#
# IMPORTANTE (artefactos): artifacts/*.joblib y *.parquet estan gitignored.
# Antes de construir la imagen deben existir en el working tree:
#   python -m src.models.producto_promesa_riesgo   # genera el .joblib (~13 MB)
#   python -m src.serving.build_lookups            # hornea artifacts/serving/
#
# Build y ejecucion:
#   docker build -t vertex-olist-api .
#   docker run --rm -p 8000:8000 vertex-olist-api
#   curl http://localhost:8000/health              # Swagger en /docs
#
# Smoke test del unpickle dentro del contenedor (salvaguarda D-39):
#   docker run --rm vertex-olist-api python -c "import joblib; joblib.load('artifacts/producto_promesa_riesgo.joblib'); print('unpickle OK')"

# Misma version de Python que el venv de entrenamiento (3.11.9) - pins D-39.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libgomp1: requerida por XGBoost en imagenes slim (sin ella el build pasa
# pero el import falla en runtime - advertencia explicita de la guia del SM).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Primero requirements para aprovechar el cache de capas de Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# src/ completo: el unpickle del escudo referencia src.features.build_dataset
# (acoplamiento del pipeline serializado, ver arquitectura_despliegue.md §2.2-D).
COPY src/ src/
# Artefactos de inferencia: modelo + lookups (gitignored != dockerignored;
# .dockerignore los permite explicitamente).
COPY artifacts/ artifacts/
# Baseline de drift para la pestana de monitoreo del dashboard.
COPY monitoring/ monitoring/

EXPOSE 8000

# healthcheck nativo de Docker contra /health (503 si el artefacto no cargo).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# 0.0.0.0: sin esto el puerto no es accesible desde fuera del contenedor.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

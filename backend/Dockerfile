# Image unique pour l'API et le worker ETL (même code, commande différente).
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY etl ./etl
COPY alembic ./alembic
COPY alembic.ini .
# Jeu de données sourcé embarqué (l'ETL peut aussi le retélécharger avec --download)
COPY --from=data raw /data/raw

# Utilisateur non root
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
# Les migrations sont appliquées au démarrage, puis l'API est lancée.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]

# Cobalt Chat API — FastAPI + SQLite
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Base SQLite dans un dossier monté en volume (persistance)
    DATABASE_URL=sqlite:////app/data/cobalt_chat.db

WORKDIR /app

# Dépendances d'abord (cache Docker)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Code applicatif
COPY main.py .
COPY src ./src

# Utilisateur non-root + dossier de données
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data \
    && chown -R app:app /app
USER app

VOLUME ["/app/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/health\", timeout=4)"

# Port fourni par l'hébergeur (Render définit $PORT), 8000 par défaut.
# Un seul worker : le gestionnaire WebSocket (présence, diffusion) est en mémoire.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]

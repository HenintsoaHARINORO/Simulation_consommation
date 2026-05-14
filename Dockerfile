# ── Build stage ───────────────────────────────────────────────────
FROM python:3.11-slim AS base

LABEL maintainer="Groowing PV Engine"
LABEL description="Moteur de simulation photovoltaïque – Architecture Hexagonale"

# Évite les fichiers .pyc et force les logs en temps réel
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ── Dépendances système minimales ─────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Dépendances Python ────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Code source ───────────────────────────────────────────────────
COPY . .

# ── Port Streamlit ────────────────────────────────────────────────
EXPOSE 8501

# ── Health check ──────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Point d'entrée ────────────────────────────────────────────────
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
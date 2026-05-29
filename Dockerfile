# ─────────────────────────────────────────────────────────────────────────────
# Project Delivery Accelerator Engine
# Single-container, offline-first Docker image
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── Labels ────────────────────────────────────────────────────────────────────
LABEL org.opencontainers.image.title="Project Delivery Accelerator Engine"
LABEL org.opencontainers.image.description="Context-aware delivery intelligence platform"
LABEL org.opencontainers.image.source="https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine"
LABEL org.opencontainers.image.licenses="MIT"

# ── OS hardening ──────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN useradd --create-home --shell /bin/bash contexta
WORKDIR /app

# ── Python dependencies (install before copying app code for layer caching) ──
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[ai]" || pip install --no-cache-dir -e .

# ── Application source ────────────────────────────────────────────────────────
COPY admin/           ./admin/
COPY ai_backends/     ./ai_backends/
COPY models/          ./models/
COPY personas/        ./personas/
COPY processors/      ./processors/
COPY static/          ./static/
COPY docs/            ./docs/
COPY sample_data/     ./sample_data/
COPY server.py        ./
COPY project_manager.py ./
COPY cli.py           ./

# ── Persistent data volume ────────────────────────────────────────────────────
# projects_data/ is mounted here so data survives container restarts.
RUN mkdir -p /data && chown contexta:contexta /data
VOLUME ["/data"]

# ── Runtime environment ────────────────────────────────────────────────────────
ENV PROJECTS_DATA_DIR=/data
ENV HOST=0.0.0.0
ENV PORT=8080

# ── Security: no default PIN — operator MUST set this ────────────────────────
# ENV ADMIN_PIN=changeme   # <-- set this via -e ADMIN_PIN=... or docker-compose

# ── Optional AI backend keys (all offline by default) ────────────────────────
# ENV GROQ_API_KEY=
# ENV OPENROUTER_API_KEY=
# ENV GEMINI_API_KEY=
# ENV AWS_ACCESS_KEY_ID=
# ENV AWS_SECRET_ACCESS_KEY=
# ENV APP_NAME="Delivery Accelerator"

# ── Switch to non-root ────────────────────────────────────────────────────────
USER contexta

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" \
    || exit 1

CMD ["python", "server.py"]

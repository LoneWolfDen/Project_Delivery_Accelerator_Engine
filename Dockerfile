# ─────────────────────────────────────────────────────────────────────────────
# Project Delivery Accelerator Engine
# Single-container, offline-first Docker image
#
# Build:  docker build -t contexta .
# Run:    docker run -p 8080:8080 -v contexta-data:/data -e ADMIN_PIN=secret contexta
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

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy manifest first so this layer is cached unless deps change.
COPY pyproject.toml ./

# Install core deps (pyyaml only) – always succeeds offline.
RUN pip install --no-cache-dir -e .

# Install AI extras separately – failures are non-fatal (cloud SDKs may not
# resolve in air-gapped builds; the app falls back to files_only mode).
RUN pip install --no-cache-dir -e ".[ai]" || true

# ── Application source ────────────────────────────────────────────────────────
COPY admin/           ./admin/
COPY ai_backends/     ./ai_backends/
COPY models/          ./models/
COPY personas/        ./personas/
COPY processors/      ./processors/
COPY static/          ./static/
COPY sample_data/     ./sample_data/
COPY server.py        ./
COPY project_manager.py ./
COPY cli.py           ./

# ── Persistent data volume ────────────────────────────────────────────────────
# Mount a named volume or host path here to persist projects across restarts.
RUN mkdir -p /data && chown contexta:contexta /data
VOLUME ["/data"]

# ── Runtime environment defaults ──────────────────────────────────────────────
ENV PROJECTS_DATA_DIR=/data \
    HOST=0.0.0.0 \
    PORT=8080 \
    APP_NAME="Project Delivery Accelerator Engine"

# AI backend keys — override at runtime; never bake secrets into the image.
# ENV ADMIN_PIN=
# ENV GROQ_API_KEY=
# ENV OPENROUTER_API_KEY=
# ENV GEMINI_API_KEY=
# ENV AWS_ACCESS_KEY_ID=
# ENV AWS_SECRET_ACCESS_KEY=
# ENV AWS_DEFAULT_REGION=us-east-1
# ENV OLLAMA_HOST=http://ollama:11434   # set automatically by docker-compose

# ── Switch to non-root ────────────────────────────────────────────────────────
USER contexta

EXPOSE 8080

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" \
    || exit 1

CMD ["python", "server.py"]

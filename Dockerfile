# ============================================================
#  H1 Scope Watcher — Dockerfile
#  Multi-stage build for a lean production image.
# ============================================================

# ── Stage 1: dependency builder ──────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ───────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="H1 Scope Watcher" \
      org.opencontainers.image.description="Monitor HackerOne program scope changes" \
      org.opencontainers.image.licenses="MIT"

# Non-root user for security
RUN groupadd --gid 1001 watcher && \
    useradd --uid 1001 --gid watcher --shell /bin/sh --create-home watcher

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=watcher:watcher . .

# Snapshots volume — persist state across container restarts
VOLUME ["/app/snapshots"]

USER watcher

ENTRYPOINT ["python", "main.py"]
CMD ["--config", "config.yaml"]

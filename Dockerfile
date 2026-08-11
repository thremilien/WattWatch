# syntax=docker/dockerfile:1

# ---- Stage 1: build the Svelte frontend -------------------------------------
FROM node:24-alpine AS frontend

WORKDIR /build

# Copy manifests first so dependency installation is cached independently of source.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


# ---- Stage 2: runtime -------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies as their own layer so app-code edits don't re-resolve them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY README.md ./
COPY wattwatch/ ./wattwatch/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY --from=frontend /build/dist ./frontend/dist

ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_PATH=/data/wattwatch.db \
    FRONTEND_DIST=/app/frontend/dist

# Run unprivileged. /data is created and owned here so a named volume mounted
# over it inherits the right ownership.
RUN useradd --system --uid 10001 --create-home --home-dir /home/wattwatch wattwatch \
    && mkdir -p /data \
    && chown -R wattwatch:wattwatch /data /app
USER wattwatch

EXPOSE 8420
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8420/api/health', timeout=3).status == 200 else 1)"

# --proxy-headers so the Secure cookie flag and client IPs are correct behind Traefik.
CMD ["uvicorn", "wattwatch.main:app", \
     "--host", "0.0.0.0", "--port", "8420", \
     "--proxy-headers", "--forwarded-allow-ips=*"]

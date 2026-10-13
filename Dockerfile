# syntax=docker/dockerfile:1
ARG BASE_IMAGE=python:3.11-slim

# ==============================================================================
# Stage 1: Build & Dependency Resolution
# ==============================================================================
FROM ${BASE_IMAGE} AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# Stage 2: Hardened Runtime Container
# ==============================================================================
FROM ${BASE_IMAGE} AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    LLM_MODE=replay \
    PATH="/home/appuser/.local/bin:${PATH}"

# Install curl for container health check probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security hardening: Non-root application user
RUN useradd -m -u 1000 appuser

# Copy installed python dependencies from builder stage
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy project source code and assets
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Dynamic PORT binding for cloud hosts (Render, Koyeb, Railway)
CMD exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000}

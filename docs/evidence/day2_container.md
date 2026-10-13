# Day 2 Evidence: Container Image Build & Public Registry Push (Task T2.5)

> **Project:** MerchantGuard (Dispute & Margin Recovery Copilot)  
> **Event:** AMD Developer Hackathon: ACT III — Track: Reinvent Commerce  
> **Milestone:** Task T2.5 Containerization & Public Registry Verification  
> **Date:** October 13, 2026

---

## 1. Public Registry Image Identifiers

As required for hackathon submission and external judge evaluation, the production container image is designated under the following canonical public registry URIs:

| Registry | Image Identifier | Description |
|---|---|---|
| **GitHub Container Registry (GHCR)** | `ghcr.io/okywoww/merchantguard:latest` | Automated CI multi-stage build via GitHub Actions |
| **Docker Hub Registry** | `docker.io/okywoww/merchantguard:latest` | Docker Hub public namespace |

---

## 2. Hardened Multi-Stage Dockerfile Architecture

The container is structured using a hardened 2-stage build in `Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1
ARG BASE_IMAGE=python:3.11-slim

# Stage 1: Build dependencies with compiler tooling
FROM ${BASE_IMAGE} AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Hardened runtime without build compilers
FROM ${BASE_IMAGE} AS runner
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    LLM_MODE=replay \
    PATH="/home/appuser/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 appuser

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Key Security & Operational Properties:
1. **Dynamic Base Image:** Supports `ARG BASE_IMAGE` so the container can start from standard `python:3.11-slim` or be built against AMD ROCm base images (`rocm/dev-ubuntu-22.04:6.0`).
2. **Non-Root Execution:** Container runs strictly as unprivileged user `appuser` (UID 1000), preventing container breakouts.
3. **Dynamic Port Binding:** Binds to `${PORT:-8000}` at runtime, guaranteeing compatibility with cloud providers (Render, Koyeb, Railway).
4. **Active Liveness Probe:** Integrated container `HEALTHCHECK` querying `GET /health`.

---

## 3. Automated CI/CD Publishing Pipeline (GitHub Actions)

A dedicated GitHub Actions workflow is defined in `.github/workflows/docker.yml`:
- **Trigger:** On every push to `main` branch or manual `workflow_dispatch`.
- **Builder:** `docker/setup-buildx-action` running on `ubuntu-latest`.
- **Authentication:** Automatic login via `secrets.GITHUB_TOKEN` to `ghcr.io`.
- **Push Destination:** `ghcr.io/okywoww/merchantguard:latest` and short-SHA commit tag.

---

## 4. Manual Local / Docker Hub Build & Push Commands

If building and pushing via standard Docker CLI:

```bash
# 1. Login to Docker Hub or GHCR
docker login

# 2. Build multi-stage image with tag
docker build -t okywoww/merchantguard:latest .

# 3. Push to Docker Hub
docker push okywoww/merchantguard:latest

# (Alternative) Tag and push to GHCR
docker tag okywoww/merchantguard:latest ghcr.io/okywoww/merchantguard:latest
docker push ghcr.io/okywoww/merchantguard:latest
```

---

## 5. Judge Verification & Pull Command

Judges and evaluators can pull and run the pre-built public image using one command:

```bash
# Pull container from public registry
docker pull ghcr.io/okywoww/merchantguard:latest

# Run container locally on port 8000
docker run -d --rm -p 8000:8000 --name merchantguard_eval ghcr.io/okywoww/merchantguard:latest

# Verify health endpoint
curl -f http://localhost:8000/health
```

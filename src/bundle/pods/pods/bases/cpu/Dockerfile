FROM python:3.12-slim AS base

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv && \
    pip install --upgrade pip setuptools wheel

WORKDIR /app

# -- prod: install from PyPI, no build context needed -------------------------
FROM base AS prod
ARG BUNDLE_VERSION=latest
RUN if [ "$BUNDLE_VERSION" = "latest" ]; then \
        pip install thebundle; \
    else \
        pip install "thebundle==${BUNDLE_VERSION}"; \
    fi

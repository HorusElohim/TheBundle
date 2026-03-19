FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    BUNDLE_SOURCE=/opt/thebundle

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv && \
    pip install --upgrade pip setuptools wheel

# Install thebundle runtime dependencies so they're baked into the image.
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY install_bundle.sh /usr/local/bin/install_bundle.sh
RUN chmod +x /usr/local/bin/install_bundle.sh

WORKDIR /app

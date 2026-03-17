# SPDX-FileCopyrightText: 2025-2026 HorusElohim
#
# SPDX-License-Identifier: GPL-3.0-only

# Build ComfyUI once, then copy only required runtime artifacts.
FROM python:3.12-slim AS builder

ARG COMFYUI_VERSION=master

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch ${COMFYUI_VERSION} https://github.com/comfyanonymous/ComfyUI /opt/ComfyUI

RUN python3 -m venv /opt/ComfyUI.venv

# Install ComfyUI deps + CUDA torch into the same venv to avoid expensive stage merges.
RUN . /opt/ComfyUI.venv/bin/activate && \
    pip install --no-cache-dir --quiet -r /opt/ComfyUI/requirements.txt && \
    pip install --no-cache-dir --quiet torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu128

FROM python:3.12-slim AS nvidia
ENTRYPOINT ["/bin/bash", "/usr/local/bin/entrypoint.sh"]

ENV CORS_HEADER=* \
    CPU_ONLY=false \
    GPU_ONLY=false \
    LISTEN_ADDR=0.0.0.0 \
    MAX_UPLOAD_MB=100 \
    SPLIT_CROSS_ATTENTION=false \
    XDG_CACHE_HOME=/opt/content/cache \
    VRAM=auto

EXPOSE 8188
STOPSIGNAL SIGINT
WORKDIR /opt/ComfyUI

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /etc/ssl/private/ /opt/content /opt/ComfyUI /opt/ComfyUI.venv /tmp/comfyui /opt/ComfyUI/user /opt/bootstrap \
    && chown -R nobody:nogroup /etc/ssl/private/ /opt/content /opt/ComfyUI /opt/ComfyUI.venv /tmp/comfyui /opt/bootstrap

COPY --chown=nobody:nogroup --from=builder /opt/ComfyUI /opt/ComfyUI
COPY --chown=nobody:nogroup --from=builder /opt/ComfyUI.venv /opt/ComfyUI.venv
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY bootstrap/install_nodes_once.sh /opt/bootstrap/install_nodes_once.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /opt/bootstrap/install_nodes_once.sh

USER nobody
VOLUME /etc/ssl/private/ /opt/ComfyUI/user /opt/content /tmp/comfyui

ARG COMFYUI_VERSION=master
ENV COMFYUI_VERSION=${COMFYUI_VERSION}

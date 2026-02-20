FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    git \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    zsh \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && \
    pip install --upgrade pip setuptools wheel

# Install CUDA-enabled torch first so PPISP extension can compile against it.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
ARG TORCH_PACKAGES="torch torchvision torchaudio"
RUN pip install --index-url ${TORCH_INDEX_URL} ${TORCH_PACKAGES}

WORKDIR /workspace
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

ARG CUDA_IMAGE=nvidia/cuda:12.8.1-devel-ubuntu24.04
FROM ${CUDA_IMAGE}

# Re-apply Python + venv setup (can't inherit from base-cpu because
# CUDA must come from the official NVIDIA image).

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-} \
    CUDA_HOME=/usr/local/cuda \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    BUNDLE_SOURCE=/opt/thebundle

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-venv \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && \
    pip install --upgrade pip setuptools wheel

# Install thebundle runtime dependencies so they're baked into the image.
# At runtime, install_bundle.sh links the mounted source via .pth —
# deps are already here, no pip install -e needed.
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY install_bundle.sh /usr/local/bin/install_bundle.sh
RUN chmod +x /usr/local/bin/install_bundle.sh

WORKDIR /app

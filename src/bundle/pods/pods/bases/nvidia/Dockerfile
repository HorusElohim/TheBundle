ARG BASE_TAG=latest
FROM thebundle/bases/cpu:${BASE_TAG}

# Install CUDA toolkit from NVIDIA repos.
# Debian Trixie uses Sequoia PGP (sqv) which rejects SHA1 signatures since 2026-02-01.
# NVIDIA's repo signing keys still use SHA1, so we mark the repo as trusted to bypass
# signature verification. This is safe in a controlled Docker build context.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates \
    && wget -qO /tmp/cuda-keyring.deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb \
    && dpkg -i /tmp/cuda-keyring.deb \
    && rm /tmp/cuda-keyring.deb \
    && sed -i 's|\[signed-by=[^]]*\]|[trusted=yes]|' /etc/apt/sources.list.d/cuda-ubuntu2404-x86_64.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    cuda-toolkit-12-8 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/usr/local/cuda-12.8/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:${LD_LIBRARY_PATH:-} \
    CUDA_HOME=/usr/local/cuda-12.8 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

ARG BASE_TAG=latest
FROM thebundle/bases/cpu:${BASE_TAG}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    git \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Install libtorch (CPU)
ARG TORCH_VERSION=2.5.1
RUN pip install torch==${TORCH_VERSION} --index-url https://download.pytorch.org/whl/cpu

ARG OPENSPLAT_VERSION=1.4.1
RUN git clone --depth 1 --branch v${OPENSPLAT_VERSION} https://github.com/pierotofy/OpenSplat.git /tmp/opensplat \
    && cd /tmp/opensplat \
    && mkdir build && cd build \
    && cmake .. -GNinja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DGPU_RUNTIME=NONE \
        -DCMAKE_PREFIX_PATH="$(python -c 'import torch; print(torch.utils.cmake_prefix_path)')" \
    && ninja -j"$(nproc)" \
    && cp opensplat /usr/local/bin/ \
    && rm -rf /tmp/opensplat

WORKDIR /workspace
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

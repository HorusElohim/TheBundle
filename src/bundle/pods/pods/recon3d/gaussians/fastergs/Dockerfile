ARG BASE_TAG=latest
FROM thebundle/bases/torch:${BASE_TAG}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    cmake \
    ninja-build \
    libgl1-mesa-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV FORCE_CUDA=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
ENV TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6;9.0+PTX"

# NeRFICG host repo drives training; Faster-GS is a method installed into it.
ARG NERFICG_REF=main
RUN git clone --depth 1 --branch ${NERFICG_REF} \
    https://github.com/nerficg-project/nerficg.git /opt/nerficg

WORKDIR /opt/nerficg
RUN pip install --no-build-isolation -r requirements.txt || true

# Faster-GS CUDA backend + method registration.
ARG FASTERGS_REF=main
RUN pip install --no-build-isolation \
    "git+https://github.com/nerficg-project/faster-gaussian-splatting.git@${FASTERGS_REF}#subdirectory=FasterGSCudaBackend" \
 && pip install --no-build-isolation \
    "git+https://github.com/nerficg-project/faster-gaussian-splatting.git@${FASTERGS_REF}"

COPY train_fastergs.py /opt/train_fastergs.py

WORKDIR /workspace
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /opt/train_fastergs.py

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

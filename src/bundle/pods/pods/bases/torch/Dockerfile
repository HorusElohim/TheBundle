ARG BASE_TAG=latest
FROM thebundle/bases/nvidia:${BASE_TAG}

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
ARG TORCH_PACKAGES="torch torchvision torchaudio"
RUN pip install --index-url ${TORCH_INDEX_URL} ${TORCH_PACKAGES}

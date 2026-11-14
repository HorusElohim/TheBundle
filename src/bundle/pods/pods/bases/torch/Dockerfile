ARG BASE_TAG=latest
FROM thebundle/bases/nvidia:${BASE_TAG}

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128

RUN pip install --resume-retries 10 tensorrt
RUN pip install --index-url ${TORCH_INDEX_URL} --resume-retries 10 torchaudio
RUN pip install --index-url ${TORCH_INDEX_URL} --resume-retries 10 torchvision

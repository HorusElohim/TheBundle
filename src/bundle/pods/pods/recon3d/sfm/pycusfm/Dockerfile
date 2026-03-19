ARG BASE_TAG=latest
FROM thebundle/bases/torch:${BASE_TAG}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

ARG PYCUSFM_VERSION=main
RUN git clone --depth 1 --branch ${PYCUSFM_VERSION} https://github.com/nvidia-isaac/pyCuSFM.git /opt/pycusfm

WORKDIR /opt/pycusfm
RUN ./setup.bash cuda12

WORKDIR /workspace
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

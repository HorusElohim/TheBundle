ARG BASE_TAG=latest
FROM thebundle/bases/torch:${BASE_TAG}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    gcc-11 \
    g++-11 \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 100 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 100

# numpy<2.0 required by 3dgrut
RUN pip install "numpy<2.0"

ARG GRUT_VERSION=main
RUN git clone --recursive --depth 1 --branch ${GRUT_VERSION} \
    https://github.com/nv-tlabs/3dgrut.git /opt/3dgrut

WORKDIR /opt/3dgrut
RUN pip install -e ".[dev]" --no-build-isolation

WORKDIR /workspace
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

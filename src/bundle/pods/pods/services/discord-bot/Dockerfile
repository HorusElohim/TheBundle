ARG BASE_TAG=latest

FROM python:3.12-slim AS opus-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG OPUS_VERSION=1.6.1
ARG OPUS_SHA256=6ffcb593207be92584df15b32466ed64bbec99109f007c82205f0194572411a1

WORKDIR /tmp/opus
RUN curl -fsSL "https://downloads.xiph.org/releases/opus/opus-${OPUS_VERSION}.tar.gz" -o opus.tar.gz \
    && echo "${OPUS_SHA256}  opus.tar.gz" | sha256sum -c - \
    && tar xzf opus.tar.gz --strip-components=1 \
    && ./configure --prefix=/usr/local --disable-static --disable-doc --disable-extra-programs \
    && make -j"$(nproc)" \
    && make install

FROM thebundle/bases/cpu:${BASE_TAG}

RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --from=opus-builder /usr/local/lib/libopus* /usr/local/lib/
RUN ldconfig

RUN pip install "thebundle[discord,youtube]"

CMD ["bundle", "discord", "start"]

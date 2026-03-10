FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv && \
    pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY pyproject.toml README.md MANIFEST.in ./
COPY .git ./.git
COPY src ./src

RUN pip install ".[discord,youtube]" && rm -rf .git

# -- Build libopus 1.6.1 from source for better music encoding quality --------
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

# -- Runtime -------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install libopus 1.6.1 built from source (replaces Debian's 1.3.1)
COPY --from=opus-builder /usr/local/lib/libopus* /usr/local/lib/
RUN ldconfig

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

CMD ["bundle", "discord", "start"]

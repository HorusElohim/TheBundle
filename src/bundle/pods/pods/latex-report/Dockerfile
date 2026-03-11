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

RUN pip install ".[report]" && rm -rf .git

FROM python:3.12-slim AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

ENTRYPOINT ["python", "-m", "bundle.perf_report.report"]
CMD ["--input-path", "/data/references", "--output-dir", "/data/performances"]

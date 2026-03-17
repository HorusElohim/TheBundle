ARG BASE_TAG=latest
FROM thebundle/bases/cpu:${BASE_TAG}

RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "thebundle[report]"

ENTRYPOINT ["bundle", "perf-report", "generate"]
CMD ["--input-path", "/data/references", "--output-dir", "/data/performances"]

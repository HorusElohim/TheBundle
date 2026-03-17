ARG BASE_TAG=latest
FROM thebundle/bases/cpu:${BASE_TAG}

RUN pip install "thebundle[website]"

EXPOSE 8000

CMD ["bundle", "website", "site", "start", "bundle", "--host", "0.0.0.0", "--port", "8000"]

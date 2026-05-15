ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY reducto ./reducto

RUN pip install --no-cache-dir ".[embeddings]"

ENV REDUCTO_DATA_DIR=/data
RUN mkdir -p /data && chmod 777 /data

ENTRYPOINT ["reducto"]
CMD ["--help"]

ARG GO_VERSION=1.24
ARG PYTHON_VERSION=3.12

FROM golang:${GO_VERSION}-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /build

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o reducto ./cmd/reducto

FROM python:${PYTHON_VERSION}-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY --from=builder /build/reducto /usr/local/bin/reducto
COPY python /app/python

RUN uv pip install --system /app/python

RUN mkdir -p /data && chmod 777 /data
ENV REDUCTO_DATA_DIR=/data

ENTRYPOINT ["reducto"]
CMD ["--help"]

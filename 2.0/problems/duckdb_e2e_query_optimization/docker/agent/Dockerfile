FROM ubuntu:24.04

ARG DUCKDB_REF=v1.5.3
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        ccache \
        cmake \
        git \
        ninja-build \
        pkg-config \
        python3 \
        python3-pip \
        curl \
        ripgrep && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --branch "${DUCKDB_REF}" --depth 1 https://github.com/duckdb/duckdb.git /app/duckdb && \
    cd /app/duckdb && \
    git submodule update --init --recursive

WORKDIR /app

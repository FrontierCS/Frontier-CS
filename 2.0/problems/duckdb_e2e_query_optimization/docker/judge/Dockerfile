# syntax=docker/dockerfile:1.7
FROM ubuntu:24.04

ARG DUCKDB_REF=v1.5.3
ARG DUCKDB_BUILD_JOBS=1
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
        python3 && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --branch "${DUCKDB_REF}" --depth 1 https://github.com/duckdb/duckdb.git /opt/duckdb-clean && \
    cd /opt/duckdb-clean && \
    git submodule update --init --recursive

RUN --mount=type=cache,target=/root/.cache/ccache \
    cd /opt/duckdb-clean && \
    GEN=ninja CMAKE_BUILD_PARALLEL_LEVEL="${DUCKDB_BUILD_JOBS}" DISABLE_UNITY=1 DISABLE_PARQUET=1 BUILD_JEMALLOC=0 BUILD_UNITTESTS=0 BUILD_BENCHMARK=1 BUILD_EXTENSIONS='tpch' make -j"${DUCKDB_BUILD_JOBS}" && \
    cp -a /opt/duckdb-clean /opt/duckdb-vanilla

WORKDIR /judge

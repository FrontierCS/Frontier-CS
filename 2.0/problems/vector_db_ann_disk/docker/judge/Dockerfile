# Judge base image for the vector_db_ann_disk task.
#
# Builds the hidden SIFT100M benchmark data FROM SCRATCH at image-build time
# (download real BIGANN base/query + official ground truth, compile
# FreshDiskANN-baseline, build the on-disk graph + PQ, measure the baseline) and
# bakes it into the image so the judge reads it locally with zero per-trial work.
# The duckdb-e2e / vllm bake pattern, but the data is constructed, not staged.
#
# Multi-stage: the heavy build toolchain (MKL, liburing, the FreshDiskANN
# compile) stays in the builder; the final image carries only /data + ENV. The
# Frontier-CS 2.0 adapter then layers cargo/rustc + numpy/faiss on top.
#
# Build context must be the docker/ directory (so the build scripts are visible):
#   docker build -f judge/Dockerfile -t <judge_tag> .
#
# Build is NETWORK + RESOURCE heavy at full scale (N=100M ~ tens of GB, hours,
# large RAM). Override scale for a quick smoke build:
#   docker build -f judge/Dockerfile --build-arg N=100000 --build-arg Q=1000 -t <tag> .

# ---- builder: construct /data ------------------------------------------------
FROM ubuntu:24.04 AS builder
ARG DEBIAN_FRONTEND=noninteractive
ARG N=100000000
ARG Q=10000

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash ca-certificates coreutils curl git \
        build-essential cmake g++ \
        libaio-dev libgoogle-perftools-dev libboost-dev \
        intel-mkl \
        python3 python3-pip python3-numpy && \
    pip3 install --break-system-packages --no-cache-dir faiss-cpu && \
    rm -rf /var/lib/apt/lists/*

COPY build_data.py build_index.sh build_baseline.py build_all.sh /opt/build/
ENV FRONTIER_VECTOR_DB_N=${N} \
    FRONTIER_VECTOR_DB_Q=${Q} \
    FRONTIER_VECTOR_DB_TOP_K=10
RUN bash /opt/build/build_all.sh /data

# ---- final: only the data + evaluator ENV ------------------------------------
FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
# N/Q match the data built above (default 100M/10k); a smoke build stays
# self-consistent (ENV matches the small baked data).
ARG N=100000000
ARG Q=10000
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /data /data

# Defense in depth: the candidate service is built+run by the judge in this same
# container. The /load files under /data/index_100M must stay world-readable, but
# the ground truth + baseline are restricted to root (the evaluator runs as root
# and additionally removes them from disk once loaded into memory — see
# evaluator.py). This blocks any non-root candidate from reading them directly.
RUN chmod 700 /data/private_100M && chmod 600 /data/private_100M/* && \
    chmod -R a+rX /data/index_100M

# Evaluator configuration. The adapter does not render this task's data paths
# into the judge, so they are pinned here as image ENV. Only the /load files live
# under /data/index_100M; truth/baseline are isolated under /data/private_100M
# and never referenced by /load.
ENV FRONTIER_VECTOR_DB_N=${N} \
    FRONTIER_VECTOR_DB_Q=${Q} \
    FRONTIER_VECTOR_DB_ITER_Q=2000 \
    FRONTIER_VECTOR_DB_VECTOR_DTYPE=uint8 \
    FRONTIER_VECTOR_DB_QUERY_DTYPE=uint8 \
    FRONTIER_VECTOR_DB_SMOKE_ONLY=0 \
    FRONTIER_VECTOR_DB_VECTOR_PATH=/data/index_100M/100M.u8bin \
    FRONTIER_VECTOR_DB_INDEX_PATH=/data/index_100M/100M_disk.index \
    FRONTIER_VECTOR_DB_PQ_PIVOTS_PATH=/data/index_100M/100M_pq_pivots.bin \
    FRONTIER_VECTOR_DB_PQ_COMPRESSED_PATH=/data/index_100M/100M_pq_compressed.bin \
    FRONTIER_VECTOR_DB_QUERY_PATH=/data/index_100M/query.bin \
    FRONTIER_VECTOR_DB_TRUTH_PATH=/data/private_100M/truth.bin \
    FRONTIER_VECTOR_DB_BASELINE_PATH=/data/private_100M/baseline.json \
    FRONTIER_VECTOR_DB_CACHE=/tmp/frontier_vector_db_ann_disk_cache

WORKDIR /judge

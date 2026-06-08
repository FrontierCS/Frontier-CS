# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ARG GENERALS_BOTS_COMMIT=c2b77bf72812ec91fb2024d80d90112b961dfa7e

ENV XLA_FLAGS="--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1" \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends bash ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "git+https://github.com/strakam/generals-bots.git@${GENERALS_BOTS_COMMIT}" \
    "jax[cpu]>=0.4.30" \
    "jaxlib>=0.4.30"

WORKDIR /app
COPY harbor/app/generals_agent /app/generals_agent
RUN git -C /app/generals_agent init -q && \
    git -C /app/generals_agent config user.email frontier-cs@example.invalid && \
    git -C /app/generals_agent config user.name "Frontier-CS" && \
    git -C /app/generals_agent add . && \
    git -C /app/generals_agent commit -q -m base

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

COPY harbor/app/generals_agent /opt/generals-agent-clean
RUN git -C /opt/generals-agent-clean init -q && \
    git -C /opt/generals-agent-clean config user.email frontier-cs@example.invalid && \
    git -C /opt/generals-agent-clean config user.name "Frontier-CS Judge" && \
    git -C /opt/generals-agent-clean add . && \
    git -C /opt/generals-agent-clean commit -q -m base

WORKDIR /judge

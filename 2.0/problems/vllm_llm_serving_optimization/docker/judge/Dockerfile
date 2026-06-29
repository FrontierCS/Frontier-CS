# Judge base image for the vLLM LLM-serving optimization task.
#
# Contains the clean upstream vLLM source (the build/baseline reference), the
# shared serving/eval harness, the SWE-bench resolve-rate harness, the Modal +
# OpenAI + datasets clients, and the Docker CLI for per-instance SWE-bench
# testbeds. The Frontier-CS 2.0 adapter builds the final judge image ON TOP of
# this one (copying judge_server.py + problem_evaluator.py into /judge).
#
# Build context must be the task directory (so `serving_eval` is visible):
#   docker build -f docker/judge/Dockerfile -t <judge_tag> .
FROM ubuntu:24.04

ARG VLLM_REF=v0.11.0
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-pip \
        python3-venv \
        ripgrep \
        docker.io && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir \
        modal \
        openai \
        "datasets>=2.19" \
        huggingface-hub \
        "swebench>=3.0"

# Clean upstream vLLM source: the build/serve baseline and the tree the patch is
# applied to. Must match the agent image's pinned tag.
RUN git clone --branch "${VLLM_REF}" --depth 1 https://github.com/vllm-project/vllm.git /opt/vllm-clean

# Shared serving/eval harness (importable as `serving_eval` from /opt).
COPY serving_eval /opt/serving_eval

# Baseline-metrics cache directory. The judge measures the vanilla baseline once
# (or reads a precomputed cache here) and never serves baseline + patched at the
# same time, honouring the one-L40S-per-environment budget.
RUN mkdir -p /opt/vllm-baseline

WORKDIR /judge

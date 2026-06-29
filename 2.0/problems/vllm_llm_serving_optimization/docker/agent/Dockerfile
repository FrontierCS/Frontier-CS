# Agent base image for the vLLM LLM-serving optimization task.
#
# Provides a CLEAN upstream vLLM checkout (no continuum / no reference solution)
# for the agent to modify, the shared serving/eval harness used by the async
# public test, and the Modal + OpenAI + datasets clients. The Frontier-CS 2.0
# adapter builds the final agent image ON TOP of this one and copies the harbor
# app scripts (make_submission.sh, public_test.sh, ...) into /app.
#
# Build context must be the task directory (so `serving_eval` is visible):
#   docker build -f docker/agent/Dockerfile -t <agent_tag> .
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
        ripgrep && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir \
        modal \
        openai \
        "datasets>=2.19" \
        huggingface-hub

# Clean upstream vLLM source for the agent to modify. This is intentionally the
# vanilla vLLM project at a pinned tag: the optimization must be re-derived by
# the agent, not copied from any reference implementation.
RUN git clone --branch "${VLLM_REF}" --depth 1 https://github.com/vllm-project/vllm.git /app/vllm

# Shared serving/eval harness (importable as `serving_eval` from /opt) used by
# the async public test client.
COPY serving_eval /opt/serving_eval

# Optional baseline-metrics cache. When present (precomputed on the clean tree),
# the public test reports a provisional speedup/score; otherwise it reports raw
# latency and accuracy only.
RUN mkdir -p /opt/vllm-baseline

WORKDIR /app

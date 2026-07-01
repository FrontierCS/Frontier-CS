# Agent image for kmeans_gpu_kernel_optimization.
#
# Light image (no torch/triton): the agent edits /app/kmeanslib and runs the
# public test, which offloads timing to a Modal GPU (torch/triton live on the
# Modal image defined in flash_gpu.py). Needs MODAL_TOKEN_ID / MODAL_TOKEN_SECRET
# in the environment to run the GPU public test.
#
# Build context = the task directory:
#   docker build -f docker/agent/Dockerfile -t <agent_tag> .
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash ca-certificates git python3 python3-pip ripgrep && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir modal

# The package the agent edits (git-tracked so make_submission.sh can diff it).
WORKDIR /app
COPY kmeanslib /app/kmeanslib
RUN printf '%s\n' '__pycache__/' '*.pyc' > /app/.gitignore && \
    git -C /app init -q && \
    git -C /app config user.email task@frontier-cs && \
    git -C /app config user.name frontier-cs && \
    git -C /app add -A -- kmeanslib .gitignore && \
    git -C /app -c commit.gpgsign=false commit -qm "pristine kmeanslib"

# Shared Modal GPU harness + the frozen naive baseline (the public-test speed
# denominator). The baseline is exactly the code the agent starts from, so it is
# not secret.
COPY flash_gpu.py /opt/flash_gpu.py
COPY judge/refkmeans.py /opt/kmeans_ref/refkmeans.py

# Agent image for truncated_svd_gpu_kernel_optimization.
# Bundles a clean, git-tracked copy of the tsvdlib package at /app/tsvdlib
# so the agent can edit it and `make_submission.sh` can diff it. torch + triton
# come from the PyTorch base image.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash ca-certificates git ripgrep && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -c "import torch, triton; print('torch', torch.__version__, 'triton', triton.__version__)"

WORKDIR /app
COPY tsvdlib /app/tsvdlib
RUN printf '%s\n' '__pycache__/' '*.pyc' > /app/.gitignore && \
    git -C /app init -q && \
    git -C /app config user.email task@frontier-cs && \
    git -C /app config user.name frontier-cs && \
    git -C /app add -A -- tsvdlib .gitignore && \
    git -C /app -c commit.gpgsign=false commit -qm "pristine tsvdlib"

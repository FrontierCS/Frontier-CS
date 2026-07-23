# Judge image for kmeans_gpu_kernel_optimization.
#
# Light image (no torch/triton): the judge validates + applies the patch and
# offloads timing to a Modal GPU (torch/triton live on the Modal image defined
# in flash_gpu.py). Needs MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in the environment.
# The Frontier-CS 2.0 adapter builds the final judge image ON TOP of this one.
#
# Build context = the task directory:
#   docker build -f docker/judge/Dockerfile -t <judge_tag> .
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash ca-certificates git python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir modal

# Pristine tree the patch is applied to, the frozen naive baseline (speed
# denominator + quality oracle), and the shared Modal GPU harness.
COPY kmeanslib /opt/kmeanslib-clean/kmeanslib
COPY judge/refkmeans.py /opt/kmeans_ref/refkmeans.py
COPY flash_gpu.py /opt/flash_gpu.py

WORKDIR /judge

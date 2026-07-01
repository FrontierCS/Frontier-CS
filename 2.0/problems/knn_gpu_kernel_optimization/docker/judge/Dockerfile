# Judge image for knn_gpu_kernel_optimization.
# Bakes the pristine package tree the agent patch is applied to
# (/opt/knnlib-clean/knnlib) and the frozen naive baseline the judge times
# against (/opt/knn_ref/refknn.py). torch + triton come from the base.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -c "import torch, triton; print('torch', torch.__version__, 'triton', triton.__version__)"

COPY knnlib /opt/knnlib-clean/knnlib
COPY judge/refknn.py /opt/knn_ref/refknn.py

WORKDIR /judge

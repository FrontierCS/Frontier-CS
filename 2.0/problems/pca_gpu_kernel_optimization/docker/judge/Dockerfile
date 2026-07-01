# Judge image for pca_gpu_kernel_optimization.
# Bakes the pristine package tree the agent patch is applied to
# (/opt/pcalib-clean/pcalib) and the frozen naive baseline the judge times
# against (/opt/pca_ref/refpca.py). torch + triton come from the base.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -c "import torch, triton; print('torch', torch.__version__, 'triton', triton.__version__)"

COPY pcalib /opt/pcalib-clean/pcalib
COPY judge/refpca.py /opt/pca_ref/refpca.py

WORKDIR /judge

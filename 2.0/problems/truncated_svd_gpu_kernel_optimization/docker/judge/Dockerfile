# Judge image for truncated_svd_gpu_kernel_optimization.
# Bakes the pristine package tree the agent patch is applied to
# (/opt/tsvdlib-clean/tsvdlib) and the frozen naive baseline the judge times
# against (/opt/tsvd_ref/reftsvd.py). torch + triton come from the base.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -c "import torch, triton; print('torch', torch.__version__, 'triton', triton.__version__)"

COPY tsvdlib /opt/tsvdlib-clean/tsvdlib
COPY judge/reftsvd.py /opt/tsvd_ref/reftsvd.py

WORKDIR /judge

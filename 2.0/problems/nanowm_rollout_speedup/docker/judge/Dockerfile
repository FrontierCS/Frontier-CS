# Judge image for nanowm_rollout_speedup (CPU-only; drives a Modal GPU).
# Bakes the task package + clean NanoWM checkout + L/2 CSGO ckpt + held-out CSGO
# episode subset + cached vanilla baseline; the GPU rollout runs on Modal.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 FRONTIER_NWM_PKG=/opt/nanowm/task
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates bash patch && rm -rf /var/lib/apt/lists/*
RUN pip install modal omegaconf hydra-core

WORKDIR /opt/nanowm
ARG NANOWM_COMMIT=main
RUN git clone https://github.com/simchowitzlabpublic/nano-world-model /opt/nanowm/nano-world-model && \
    cd /opt/nanowm/nano-world-model && git checkout "$NANOWM_COMMIT"
COPY task_ctx/infra_patches/ /tmp/infra_patches/
RUN cd /opt/nanowm/nano-world-model && for p in /tmp/infra_patches/*.patch; do \
        [ -e "$p" ] && git apply "$p" || true; done && \
    { grep -q 'use_deterministic_algorithms' src/sample/evaluate_metrics.py \
        && grep -q 'NWM_TIME_FILE' src/sample/rollout.py; } \
      || { echo 'FATAL: infra patch did not apply (determinism / timer markers missing)'; exit 1; }

# Hidden assets baked by build_images.sh into the build context:
#   task_ctx/assets/ckpts/nanowm-l2-csgo/model_state_dict.pt
#   task_ctx/assets/csgo/1-200/*.hdf5            (held-out episode subset)
#   task_ctx/assets/csgo_subset/{val_files.txt,val_starts.npy}
#   task_ctx/assets/baseline/baseline_metrics.json (optional precomputed)
COPY task_ctx/assets/ /opt/nanowm/
COPY task_ctx/task_pkg/ /opt/nanowm/task/
COPY task_ctx/evaluator.py /opt/nanowm/task/evaluator.py

# Modal builds the GPU image from this same checkout/assets at deploy time.
ENV FRONTIER_NWM_REPO=/opt/nanowm/nano-world-model \
    FRONTIER_NWM_CKPT=/opt/nanowm/ckpts/nanowm-l2-csgo/model_state_dict.pt \
    FRONTIER_NWM_CSGO_DATA=/opt/nanowm/data/csgo \
    FRONTIER_NWM_VAL_FILES=/opt/nanowm/data/csgo_subset/val_files.txt \
    FRONTIER_NWM_VAL_STARTS=/opt/nanowm/data/csgo_subset/val_starts.npy \
    FRONTIER_NWM_BASELINE_CACHE=/opt/nanowm/baseline/baseline_metrics.json \
    NWM_BAKE_DIR=/opt/nanowm

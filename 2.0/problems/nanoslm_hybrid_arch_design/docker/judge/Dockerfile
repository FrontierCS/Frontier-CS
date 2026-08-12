# Judge image for nanoslm_hybrid_arch_design.
#
# CPU-ONLY, AND DELIBERATELY SO. The H100 is served on Modal
# (harness/modal_app.py); this container dispatches to it and scores the
# returned metrics. It therefore installs NO torch, NO CUDA and NO
# flash-linear-attention -- those live in the Modal image, which Modal builds
# remotely from its own declarative spec.
#
# That split is load-bearing rather than incidental: `evaluator._backend()`
# picks MODAL whenever a Modal token is present, and `run_pair_remote` returns
# only plain builtins so this container can deserialize the result without
# torch. Installing a GPU stack here would be dead weight AND would mask a
# misconfiguration -- a judge that quietly falls back to LOCAL would try to
# train a ~190M model at ctx 8192 on CPU.
#
# The versions the GPU side must use are pinned
# in harness/modal_app.py:
#     torch 2.6.0+cu124 / triton 3.2.0 / flash-linear-attention 0.5.1
# That exact combination is the one whose GDN BACKWARD kernel compiles; on
# triton 3.1.0 every call hung 30+ min, and on fla 0.4.1 the backward failed to
# lower. Do not drift them independently.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

# modal: the GPU dispatch client. numpy: harness/data.py reads the uint32 token
# streams even on the judge side for shape/sanity checks. No torch by design.
RUN pip install --no-cache-dir "modal>=1.0" "numpy<2"

WORKDIR /opt/nanoslm_arch

# The task package. Preserve the DIRECTORY layout: evaluator.py does
# `from harness import policy, scoring, settings` and the harness modules use
# relative imports, so flattening breaks both.
COPY task_ctx/task_pkg/harness/ /opt/nanoslm_arch/task/harness/
COPY task_ctx/evaluator.py       /opt/nanoslm_arch/task/evaluator.py

# Hidden assets. val.bin is the HELD-OUT stream and exists ONLY here -- it is
# never copied into the agent image, and build_images.sh asserts that. Both
# streams are flat uint32 dolma2 token ids (vocab 100278), not raw bytes.
#
# manifest.json is REQUIRED, not documentation: it carries `val_bytes`, the
# denominator of the scored bits-per-byte. harness/data.py raises rather than
# normalizing by a token count, so a judge without it fails every run.
COPY task_ctx/assets/train.bin     /opt/nanoslm_arch/data/train.bin
COPY task_ctx/assets/val.bin       /opt/nanoslm_arch/data/val.bin
COPY task_ctx/assets/manifest.json /opt/nanoslm_arch/data/manifest.json
RUN mkdir -p /opt/nanoslm_arch/baseline

# Paths must match harness/settings.py TaskConfig defaults.
ENV PYTHONPATH=/opt/nanoslm_arch/task \
    NANOSLM_ARCH_ASSETS=/opt/nanoslm_arch/data

# Fail the build if the judge cannot import its own entrypoint, or if it can
# import torch (which would mean the CPU-only contract was broken and a silent
# LOCAL fallback is possible).
RUN python3 -c "\
import sys; sys.path.insert(0, '/opt/nanoslm_arch/task');\
import evaluator, harness.policy, harness.scoring, harness.settings;\
print('judge imports OK');\
"
# MUST stay ONE physical line. Docker splices a trailing `\` by deleting the
# newline, so a multi-line try/except collapses into `...)except ImportError:`
# -- a SyntaxError, which exits non-zero and thus "passed" for the wrong reason
# while never testing torch at all. find_spec also beats `import torch` here: it
# flags a present-but-broken torch, which a bare ImportError would swallow.
RUN python3 -c "import importlib.util, sys; sys.exit('FATAL: torch present in the CPU-only judge image') if importlib.util.find_spec('torch') else print('torch absent as intended')"

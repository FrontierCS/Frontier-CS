# Agent workspace image for nanoslm_hybrid_arch_design.
#
# CPU-ONLY. The agent designs an architecture and submits /app/model.py; the
# JUDGE trains it (on a Modal H100). So this image ships no torch, no CUDA and
# no corpus -- an agent cannot and need not train here.
#
# What it DOES ship is the judge's own static policy gate, so
# `bash /app/public_test.sh` runs the exact accept/reject rules the judge
# applies, instead of the agent discovering them by burning submissions.
#
# CRITICALLY: /opt/nanoslm_arch/data/val.bin -- the held-out stream -- is NOT
# here and must never be. build_images.sh asserts its absence post-build.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates curl git ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Parity with the adapter template's tooling.
RUN pip install --no-cache-dir "numpy<2" \
    && curl -fsSL https://claude.ai/install.sh | bash 2>/dev/null || true

WORKDIR /app

# Workspace scaffolding: starter model.py, README, public_test.
COPY task_ctx/harbor_app/ /app/

# The judge's static gate, shipped verbatim so the local check and the judge's
# check cannot drift. policy.py is settings-free and names no hidden value:
# it contains the DENYLIST (which is public by design and stated in the readme)
# but no thresholds, no paths, and no held-out identifiers. build_images.sh
# greps it before copying.
COPY task_ctx/agent_task/policy.py /app/policy.py
RUN chmod +x /app/*.sh 2>/dev/null || true

# Fail the build if the starter submission does not pass the shipped gate --
# an agent must never open a workspace whose default file is already rejected.
#
# Assert through public_test.sh, the SAME entrypoint the agent runs, not by
# importing check_source directly. A direct `sys.path`+import once passed here
# while `bash /app/public_test.sh` crashed, because public_test.py loads
# policy.py via spec_from_file_location and that path had its own bug. Testing
# the real entrypoint is what makes this assertion mean what it claims.
# The __pycache__ removal is load-bearing, not tidiness: running the gate
# compiles policy.py, and the resulting .pyc embeds the denylist strings
# ("val.bin", "/opt/"). build_images.sh greps every file under /app except
# policy.py itself, so leaving the byte-compiled twin behind trips that check.
RUN bash /app/public_test.sh \
    || (echo 'FATAL: shipped starter model.py fails the policy gate' && exit 1) \
    && rm -rf /app/__pycache__

# Assert the held-out stream is absent (defence in depth; build_images.sh also
# checks the built image).
RUN test ! -e /opt/nanoslm_arch/data/val.bin || \
    (echo 'FATAL: held-out val.bin present in the AGENT image' && exit 1)

# Evaluation image for formal_conjectures problems.
#
# Contains Lean 4 (pinned by the formal-conjectures lean-toolchain), a fully
# built checkout of google-deepmind/formal-conjectures (including Mathlib via
# `lake exe cache get`), and python3 for the evaluator orchestrator.
#
# FC_REF must match the tag the third_party/formal-conjectures submodule is
# pinned to — build via build.sh, which derives it from the submodule.
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates bash python3 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSf https://elan.lean-lang.org/elan-init.sh | sh -s -- -y --default-toolchain none
ENV PATH="/root/.elan/bin:${PATH}"

ARG FC_REF=bench-v1-lean4.27.0
RUN git clone --depth 1 --branch ${FC_REF} \
        https://github.com/google-deepmind/formal-conjectures /opt/formal-conjectures

WORKDIR /opt/formal-conjectures

# Mathlib olean cache, then compile the conjecture statements themselves.
# (lake 5.x has no jobs flag; parallelism follows available cores.)
RUN lake exe cache get
RUN lake build
# The upstream extractor exe, used once to generate the problem manifest.
RUN lake build extract_names

# Smoke test: a trivial standalone theorem compiles against the built package.
RUN echo 'theorem solution : True := trivial' > /tmp/smoke.lean \
    && lake env lean /tmp/smoke.lean \
    && rm /tmp/smoke.lean

# Stamp the pinned ref so the evaluator can verify image/problem consistency.
ENV FC_REF=${FC_REF}

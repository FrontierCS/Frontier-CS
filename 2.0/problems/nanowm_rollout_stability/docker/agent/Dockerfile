# Agent workspace image for nanowm_rollout_speedup (CPU-only client).
# The agent edits the NanoWM checkout under /app/nano-world-model and submits a
# patch; GPU evaluation happens on Modal (judge side). Build via ../build_images.sh.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates bash ripgrep patch && rm -rf /var/lib/apt/lists/*

# Pre-install Claude Code + Codex CLI (parity with other 2.0 agent images).
RUN curl -fsSL https://claude.ai/install.sh | bash -s -- && \
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
ENV NVM_DIR="/root/.nvm"
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash && \
    . "$NVM_DIR/nvm.sh" && nvm install 22 && nvm alias default 22 && \
    npm install -g @openai/codex@latest && ln -sf "$(which node)" /usr/local/bin/node

WORKDIR /app
# Clean NanoWM checkout the agent patches (pinned commit; native build not needed).
ARG NANOWM_COMMIT=main
RUN git clone https://github.com/simchowitzlabpublic/nano-world-model /app/nano-world-model && \
    cd /app/nano-world-model && git checkout "$NANOWM_COMMIT"
# Task-local infra patches the agent builds on (decode-OOM + get_seq_length);
# applied so the harness rollout works, outside the agent's editable scope.
COPY task_ctx/infra_patches/ /tmp/infra_patches/
RUN cd /app/nano-world-model && for p in /tmp/infra_patches/*.patch; do \
        [ -e "$p" ] && git apply "$p" || true; done && \
    { grep -q 'clip_offset' src/sample/rollout.py \
        && grep -q 'use_deterministic_algorithms' src/sample/evaluate_metrics.py; } \
      || { echo 'FATAL: infra patch did not apply (clip_offset / determinism markers missing)'; exit 1; } && \
    git add -A && git -c user.email=t@e -c user.name=t commit -q -m base || true

COPY task_ctx/harbor_app/ /app/
# NOTE: the eval package (task_pkg/stability_eval + evaluator.py) is JUDGE-ONLY and is
# deliberately NOT shipped to the agent. It carries settings.py (the scored rollout
# horizon band, seed, val-file paths, drift-tail index) and the scoring/orchestration
# source; baking it into /app/task let the agent read the judge internals directly
# (e.g. the exact rollout length / tail window). The judge image keeps it under
# /opt/nanowm/task. The agent validates patches by submitting and reading judge feedback.
RUN chmod +x /app/*.sh 2>/dev/null || true

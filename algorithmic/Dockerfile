# syntax=docker/dockerfile:1

# Use official Ubuntu 22.04 as base image
FROM ubuntu:22.04

# Set environment variable to avoid interactive prompts during apt-get installation
ENV DEBIAN_FRONTEND=noninteractive

# --- 1. Install base dependencies, language toolchains and Node.js ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    git \
    unzip \
    zip \
    build-essential \
    pkg-config \
    python3 \
    python3-pip \
    pypy3 \
    openjdk-17-jdk \
    # Install Node.js 20.x
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    # Clean apt cache
    && rm -rf /var/lib/apt/lists/*

# --- 2. Update npm to latest version ---
RUN npm install -g npm@latest

# --- 3. Install go-judge (auto-detect architecture) ---
ARG GO_JUDGE_VERSION=v1.11.1
RUN set -eux; \
  arch="$(uname -m)"; \
  case "$arch" in \
    x86_64)  goarch="amd64v2" ;; \
    aarch64) goarch="arm64" ;; \
    *) echo "Unsupported arch: $arch" && exit 1 ;; \
  esac; \
  version="${GO_JUDGE_VERSION#v}"; \
  asset="go-judge_${version}_linux_${goarch}.tar.gz"; \
  release_url="https://github.com/criyle/go-judge/releases/download/${GO_JUDGE_VERSION}"; \
  download_dir="$(mktemp -d)"; \
  curl -fsSL "${release_url}/${asset}" -o "${download_dir}/${asset}"; \
  curl -fsSL "${release_url}/checksums.txt" -o "${download_dir}/checksums.txt"; \
  (cd "$download_dir" && \
    awk -v asset="$asset" '$2 == asset { print }' checksums.txt > selected-checksum.txt && \
    test -s selected-checksum.txt && \
    sha256sum -c selected-checksum.txt && \
    tar -xzf "$asset" -C /usr/local/bin go-judge); \
  rm -rf "$download_dir"; \
  chmod +x /usr/local/bin/go-judge

# --- 4. Set application working directory and install Node.js dependencies ---
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --omit=dev --ignore-scripts

# --- 5. Copy application code and entry script ---
COPY server.js entrypoint.sh ./
COPY judge/src/ ./src/
COPY judge/include/ ./include/
COPY judge/config/ ./config/
COPY judge/include/ /lib/testlib/

# Ensure entrypoint.sh is executable and fix possible Windows line ending issues
RUN chmod +x entrypoint.sh && sed -i 's/\r$//' entrypoint.sh

# --- 6. Set default environment variables ---
# Note: JUDGE_WORKERS and GJ_PARALLELISM default to $(nproc) at runtime in entrypoint.sh
ENV PORT=8081 \
    GJ_ADDR=http://127.0.0.1:5050

# --- 7. Set container entry point ---
ENTRYPOINT ["/app/entrypoint.sh"]
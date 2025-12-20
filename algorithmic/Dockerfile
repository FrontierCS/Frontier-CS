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
    kotlin \
    rustc \
    cargo \
    golang \
    # Install Node.js 20.x
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    # Clean apt cache
    && rm -rf /var/lib/apt/lists/*

# --- 2. Update npm to latest version ---
RUN npm install -g npm@latest

# --- 3. Install go-judge (auto-detect architecture) ---
RUN set -eux; \
  arch="$(uname -m)"; \
  case "$arch" in \
    x86_64)  goarch="amd64" ;; \
    aarch64) goarch="arm64" ;; \
    *) echo "Unsupported arch: $arch" && exit 1 ;; \
  esac; \
  url=$(curl -fsSL https://api.github.com/repos/criyle/go-judge/releases/latest \
    | jq -r --arg goarch "$goarch" '.assets[] | select(.name | test("linux.*\($goarch).*tar.gz$")) | .browser_download_url' \
    | head -n 1); \
  echo "Downloading go-judge for $arch ($url)"; \
  curl -fsSL "$url" | tar -xz -C /usr/local/bin go-judge; \
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
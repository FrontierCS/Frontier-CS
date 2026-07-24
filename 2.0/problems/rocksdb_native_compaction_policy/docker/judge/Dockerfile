# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm

ARG ROCKSDB_COMMIT=4595a5e95ae8525c42e172a054435782b3479c57
ARG ROCKSDB_ARCHIVE_SHA256=9469e7d24644e298134d0464ec2d398a9b91cc401102009ec1ecde0383485d6c
ARG ROCKSDB_BUILD_JOBS=3
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        cmake \
        git \
        ninja-build \
        pkg-config \
        libgflags-dev \
        libsnappy-dev \
        zlib1g-dev \
        libbz2-dev \
        liblz4-dev \
        libzstd-dev \
        python3 && \
    rm -rf /var/lib/apt/lists/*

# Prebuild one tree for incremental candidate builds, then copy it for vanilla.
RUN python3 - "${ROCKSDB_COMMIT}" "${ROCKSDB_ARCHIVE_SHA256}" <<'PY'
import hashlib
import io
import shutil
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

commit, expected_sha256 = sys.argv[1:]
url = f"https://codeload.github.com/facebook/rocksdb/tar.gz/{commit}"
for attempt in range(5):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Frontier-CS"})
        with urllib.request.urlopen(request, timeout=30) as response:
            archive = response.read()
        actual_sha256 = hashlib.sha256(archive).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(f"archive sha256 mismatch: {actual_sha256}")
        break
    except Exception:
        if attempt == 4:
            raise
        time.sleep(3 * (attempt + 1))

extract_dir = Path("/tmp/rocksdb-extract")
shutil.rmtree(extract_dir, ignore_errors=True)
extract_dir.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as source:
    source.extractall(extract_dir, filter="data")
roots = list(extract_dir.iterdir())
if len(roots) != 1 or not roots[0].is_dir():
    raise RuntimeError("unexpected RocksDB archive layout")
shutil.move(str(roots[0]), "/opt/rocksdb-clean")
shutil.rmtree(extract_dir)
PY

RUN printf '%s\n' "${ROCKSDB_COMMIT}" \
        > /opt/rocksdb-clean/.frontier-upstream-commit && \
    git -C /opt/rocksdb-clean init -q && \
    git -C /opt/rocksdb-clean config user.name "Frontier-CS" && \
    git -C /opt/rocksdb-clean config user.email frontier-cs@example.invalid && \
    git -C /opt/rocksdb-clean add -A && \
    GIT_AUTHOR_DATE=2026-01-01T00:00:00Z \
    GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
        git -C /opt/rocksdb-clean commit -q -m "Pinned RocksDB ${ROCKSDB_COMMIT}" && \
    cd /opt/rocksdb-clean && \
    PORTABLE=1 DEBUG_LEVEL=0 DISABLE_WARNING_AS_ERROR=1 \
        make -j"${ROCKSDB_BUILD_JOBS}" static_lib && \
    cp -a /opt/rocksdb-clean /opt/rocksdb-vanilla

COPY judge/harness/lsm_policy_harness.cc /judge/harness/lsm_policy_harness.cc

WORKDIR /judge

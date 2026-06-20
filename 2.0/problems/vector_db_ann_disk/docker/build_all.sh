#!/usr/bin/env bash
# Full data-build pipeline for vector_db_ann_disk. Operator tooling, NOT
# agent-facing. Produces, with zero manual download, everything the judge needs:
#
#   <data_root>/index_100M/{100M.u8bin,query.bin,100M_disk.index,
#                           100M_pq_pivots.bin,100M_pq_compressed.bin}
#   <data_root>/private_100M/{truth.bin,baseline.json}
#
# Steps:
#   1. build_data.py   download real BIGANN base/query + slice official GT
#   2. build_index.sh  clone+compile FreshDiskANN, build the on-disk graph + PQ
#   3. build_baseline.py  exact Faiss baseline throughput
#
# Parametrized by FRONTIER_VECTOR_DB_N / _Q for small-scale testing. At full
# scale (N=100,000,000) this needs a large-RAM host, tens of GB of disk, and
# hours of compute — run it offline on the build host.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DATA_ROOT="${1:?usage: build_all.sh <data_root>}"

export FRONTIER_VECTOR_DB_N="${FRONTIER_VECTOR_DB_N:-100000000}"
export FRONTIER_VECTOR_DB_Q="${FRONTIER_VECTOR_DB_Q:-10000}"
export FRONTIER_VECTOR_DB_TOP_K="${FRONTIER_VECTOR_DB_TOP_K:-10}"

echo "=== [1/3] data (vectors + queries + ground truth) ==="
python3 "$SCRIPT_DIR/build_data.py" "$DATA_ROOT"

echo "=== [2/3] DiskANN on-disk graph + PQ ==="
bash "$SCRIPT_DIR/build_index.sh" "$DATA_ROOT"

echo "=== [3/3] reference baseline throughput ==="
python3 "$SCRIPT_DIR/build_baseline.py" "$DATA_ROOT"

echo "=== done. contents: ==="
ls -la "$DATA_ROOT/index_100M" "$DATA_ROOT/private_100M"

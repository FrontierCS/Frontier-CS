#!/usr/bin/env bash
# Build the DiskANN on-disk graph + PQ files for vector_db_ann_disk, using the
# FreshDiskANN-baseline tooling the task references. Operator tooling — runs at
# judge-image build time, NOT agent-facing.
#
#   build_index.sh <data_root>
#
# Reads  <data_root>/index_100M/100M.u8bin
# Writes <data_root>/index_100M/100M_disk.index
#        <data_root>/index_100M/100M_pq_pivots.bin
#        <data_root>/index_100M/100M_pq_compressed.bin
#
# Index parameters (tunable via env): R graph degree, L build list, B search-RAM
# budget GB (controls PQ aggressiveness — must let PQ fit the 8 GiB eval budget),
# M build-RAM budget GB, T threads.
set -euo pipefail

DATA_ROOT="${1:?usage: build_index.sh <data_root>}"
INDEX_DIR="$DATA_ROOT/index_100M"
PREFIX="$INDEX_DIR/100M"
SRC="$DATA_ROOT/100M.u8bin"
[[ -f "$INDEX_DIR/100M.u8bin" ]] || { echo "missing $INDEX_DIR/100M.u8bin (run build_data.py first)" >&2; exit 1; }

R="${FRONTIER_VECTOR_DB_GRAPH_DEGREE:-64}"
L="${FRONTIER_VECTOR_DB_BUILD_L:-128}"
B="${FRONTIER_VECTOR_DB_PQ_BUDGET_GB:-4}"
M="${FRONTIER_VECTOR_DB_BUILD_RAM_GB:-32}"
T="${FRONTIER_VECTOR_DB_BUILD_THREADS:-$(nproc)}"
REPO_DIR="${FRESHDISKANN_DIR:-/opt/FreshDiskANN-baseline}"
REPO_URL="https://github.com/g4197/FreshDiskANN-baseline.git"

if [[ -f "${PREFIX}_disk.index" && -f "${PREFIX}_pq_pivots.bin" && -f "${PREFIX}_pq_compressed.bin" ]]; then
  echo "[index] outputs exist, skip"
  exit 0
fi

# 1. Clone + build FreshDiskANN-baseline (liburing first, then cmake build).
if [[ ! -x "$REPO_DIR/build/tests/build_disk_index" ]]; then
  echo "[index] cloning + building FreshDiskANN-baseline ..."
  [[ -d "$REPO_DIR" ]] || git clone --depth 1 "$REPO_URL" "$REPO_DIR"
  ( cd "$REPO_DIR/third_party/liburing" && ./configure && make -j"$T" )
  # The upstream CMakeLists hardcodes the legacy Intel MKL layout
  # (/opt/intel/.../mkl + iomp5). When building against the apt `intel-mkl`
  # package (headers in /usr/include/mkl, no iomp5), repoint the include path
  # and switch to the GNU threading layer so it links.
  if [[ -f /usr/include/mkl/mkl.h && ! -d /opt/intel/compilers_and_libraries ]]; then
    echo "[index] patching CMakeLists for apt intel-mkl (GNU threading)"
    sed -i \
      's#link_libraries(mkl_intel_ilp64 mkl_intel_thread mkl_core iomp5 pthread m dl)#link_libraries(mkl_intel_ilp64 mkl_gnu_thread mkl_core gomp pthread m dl)\n\tinclude_directories(/usr/include/mkl)#' \
      "$REPO_DIR/CMakeLists.txt"
  fi
  mkdir -p "$REPO_DIR/build"
  ( cd "$REPO_DIR/build" && cmake -DCMAKE_BUILD_TYPE=Release .. && make -j"$T" build_disk_index )
fi

# 2. Build the disk index. dist=l2, single_file=0 (multi-file output).
echo "[index] build_disk_index R=$R L=$L B=$B M=$M T=$T on $(basename "$INDEX_DIR")/100M.u8bin"
"$REPO_DIR/build/tests/build_disk_index" \
  uint8 "$INDEX_DIR/100M.u8bin" "$PREFIX" "$R" "$L" "$B" "$M" "$T" l2 0

for f in _disk.index _pq_pivots.bin _pq_compressed.bin; do
  [[ -f "${PREFIX}${f}" ]] || { echo "[index] ERROR: expected output ${PREFIX}${f} missing" >&2; exit 1; }
done
echo "[index] done:"
ls -la "${PREFIX}_disk.index" "${PREFIX}_pq_pivots.bin" "${PREFIX}_pq_compressed.bin"

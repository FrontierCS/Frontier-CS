# Experimental vector_db_ann_disk Judge Image

This task **constructs** the hidden SIFT100M benchmark data from scratch at
judge-image build time and bakes it in (the duckdb-e2e / vllm bake pattern). No
manual download, no data hosting, no host staging — the image build downloads the
public BIGANN dataset, builds the DiskANN index, and measures the baseline.

The **agent** image stays the default `ubuntu:24.04` — the agent never sees the
hidden data; it only implements the `/load` + `/search` contract.

## Build

```bash
bash 2.0/problems/vector_db_ann_disk/docker/build_images.sh
```

Default tag (kept in sync with `config.yaml` `runtime.docker.judge_image`):

```text
JUDGE_TAG=frontiercs/vector-db-ann-disk-judge:experimental-v1
```

Full scale (N=100M) is **network / RAM / time heavy** (see Resources). Quick
smoke image at small scale:

```bash
N=100000 Q=1000 bash docker/build_images.sh
```

## Pipeline (docker/build_all.sh, run inside the image builder)

1. **build_data.py** — downloads the real BIGANN data and slices it:
   - `100M.u8bin` — first N rows of `base.1B.u8bin` via HTTP range, header
     rewritten to N (`uint8`, 128-dim).
   - `query.bin` — `query.public.10K.u8bin` (10,000 × 128 `uint8`).
   - `truth.bin` — top-`TOP_K` ids per query, sliced from the **official** exact
     ground truth `GT_100M/bigann-100M` (so no 51 GB exact-search is needed).
2. **build_index.sh** — clones + compiles
   [FreshDiskANN-baseline](https://github.com/g4197/FreshDiskANN-baseline) and runs
   `build_disk_index` → `100M_disk.index`, `100M_pq_pivots.bin`,
   `100M_pq_compressed.bin`.
3. **build_baseline.py** — exact Faiss `IndexFlatL2` throughput → `baseline.json`.

Source URLs (public, from big-ann-benchmarks):

```text
https://dl.fbaipublicfiles.com/billion-scale-ann-benchmarks/bigann/base.1B.u8bin
https://dl.fbaipublicfiles.com/billion-scale-ann-benchmarks/bigann/query.public.10K.u8bin
https://dl.fbaipublicfiles.com/billion-scale-ann-benchmarks/GT_100M/bigann-100M
```

## What the judge image contains

```text
/data/index_100M/     # handed to the candidate via /load
  100M.u8bin  query.bin  100M_disk.index  100M_pq_pivots.bin  100M_pq_compressed.bin
/data/private_100M/   # judge-only, NEVER referenced by /load
  truth.bin  baseline.json
```

Data paths, dtype, `N=100,000,000`, `Q=10,000` are pinned as image `ENV`
(`judge/Dockerfile`). The adapter builds the final judge image on top of this one,
layering `cargo`/`rustc` + `numpy`/`faiss-cpu` from `config.yaml`.

## Resources (full N=100M build)

- **base download**: ~12.8 GB (first 100M rows of `base.1B.u8bin` via range).
- **DiskANN index build**: tens of GB output, multiple cores, ~hours; tune
  `R/L/B/M/T` via env in `build_index.sh` (`B` = PQ budget; keep PQ within the
  8 GiB eval budget).
- **baseline**: exact FlatL2 over 100M holds vectors as float32 (~**51 GB RAM**)
  on the build host. The baseline therefore reflects the *build* host, not the
  8 GiB eval container — a deliberate bake. Adjust if you want a different
  reference.

## Running locally on constrained Docker (rootless / vfs / limited disk)

The baked judge image is **large (~58 GB)** because the SIFT100M data lives
inside it. On a host with `overlay2` and ample disk this is fine. But on a
**rootless daemon using the `vfs` storage driver** (no copy-on-write), every
derived image layer and every container re-copies the full image, so a single
trial can need **~3x** the image size in scratch space, and a near-full shared
disk can be exhausted.

For those hosts, use a **mount-data variant**: build a tiny base image (ubuntu +
the pinned evaluator ENV + the small `private_100M` secrets) and bind-mount the
54 GB `index_100M` read-only into the judge service at `/data/index_100M`
instead of baking it. The data then lives once on the host. Other rootless
gotchas: set `DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock`; pass
`--cpus ignore` to `harbor trial start` if the `cpu` cgroup controller is not
delegated (only `memory`/`pids` usually are); and inject agent credentials via
**env vars** (e.g. `OPENAI_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN`), since
`docker cp` of host-owned credential files fails under the user namespace.

Note also that iterative `submit.sh` evaluations time only
`FRONTIER_VECTOR_DB_ITER_Q` queries (default 2000) for fast feedback; the final
verifier (`FRONTIER_SUBMISSION_ROLE=final`) always times the full
`FRONTIER_VECTOR_DB_Q` set.

## Security note (anti-cheat)

The candidate service is built and run by the judge **in this same container**,
so plain directory isolation is not enough on its own. Three layers protect the
ground truth / baseline:

1. **Out of the /load directory** — `truth.bin` / `baseline.json` live under
   `/data/private_100M`, never passed to `/load`, so they cannot be reached via
   `dirname(vector_path)`.
2. **Restricted permissions** — `/data/private_100M` is `0700` root-only (the
   `/load` files under `/data/index_100M` stay world-readable). A non-root
   candidate cannot read them.
3. **Removed after load** — `evaluator.py` loads the truth + baseline into memory
   at judge startup and then **deletes the files from disk** before any candidate
   runs, so even a root candidate finds nothing to read. (`_ensure_benchmark`
   caches in memory; later submissions never need the files. Opt out for
   debugging with `FRONTIER_VECTOR_DB_KEEP_TRUTH=1`.)

They are also never named in the agent-facing `readme`.

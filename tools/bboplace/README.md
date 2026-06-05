BBOPlace data image
===================

The BBOPlace Frontier-CS 2.0 tasks use a separate judge image:

`ghcr.io/frontiercs/frontiercs-bboplace-data:2026-06-ispd-iccad`

The agent image stays small and does not contain the benchmark data. The judge
image must contain a pinned BBOPlace-Bench checkout plus extracted ISPD2005 and
ICCAD2015 benchmark data under `/opt/bboplace-bench`.

Expected layout:

```text
/opt/bboplace-bench/
  config/
  src/
  benchmarks/
    ispd2005/
    iccad2015/
```

The data sources, SHA256 checksums, observed sizes, and scoring constants are
tracked in `data_manifest.json`. The final image must store the extracted
`.aux`, `.nodes`, `.nets`, `.pl`, `.scl`, and `.wts` files because the
BBOPlace reader expects those filenames.

The Frontier-CS evaluator uses only the BBOPlace MGO + MP-HPWL path. It avoids
the original BBOPlace `src.evaluator` import path because that path imports
Ray, HPO, DREAMPlace, and other dependencies that are not needed for this CPU
metric. The data image therefore only needs Python, NumPy, PyYAML, the
BBOPlace `src/` and `config/` trees, and the extracted benchmarks.

The image should make benchmark files readable by the root judge process only.
Submitted solution code is run as `nobody` and receives only public benchmark
metadata through `solve(info)`.

Local validation commands:

```bash
mkdir -p /tmp/bboplace-data/benchmarks
git clone https://github.com/lamda-bbo/BBOPlace-Bench /tmp/bboplace-data/BBOPlace-Bench
git -C /tmp/bboplace-data/BBOPlace-Bench checkout 4a0dde451e40a3f368e501df6f027c442fcca02a

# Download and extract the BBOPlace-Bench README Google Drive archives:
#   ispd2005.zip -> /tmp/bboplace-data/benchmarks/ispd2005
#   iccad2015_benchmark.zip -> /tmp/bboplace-data/benchmarks/iccad2015

docker build \
  -t ghcr.io/frontiercs/frontiercs-bboplace-data:2026-06-ispd-iccad \
  -f tools/bboplace/Dockerfile.data \
  /tmp/bboplace-data

python3 tools/bboplace/check_constants.py
python3 tools/bboplace/check_generated_tasks.py /path/to/generated/frontier-cs-2.0
```

Placement visualization
-----------------------

Use `tools/bboplace/viz_placement.py` to render a submitted placement as an
SVG. The script reuses the task evaluator, so run it inside the BBOPlace judge
image or another environment where `BBOPLACE_ROOT` points at the BBOPlace-Bench
runtime and benchmark data.

Example with a Harbor best-submission payload:

```bash
docker run --rm \
  -v "$PWD":/repo \
  -v /path/to/trial/agent/best_submission_payload.json:/payload.json:ro \
  ghcr.io/frontiercs/frontiercs-bboplace-data:2026-06-ispd-iccad \
  python3 /repo/tools/bboplace/viz_placement.py \
    --problem-id bboplace_ispd2005 \
    --benchmark adaptec1 \
    --payload-json /payload.json \
    --output /repo/.frontier-cs/harbor/bboplace-viz/adaptec1.svg
```

The output SVG draws the legalized macro rectangles produced by the same MGO
placement path used for scoring. The netlist and benchmark data remain inside
the judge/data environment.

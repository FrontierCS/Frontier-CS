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
tracked in `data_manifest.json`. ISPD2005 archives contain gzipped inner files;
the final image must store the uncompressed `.aux`, `.nodes`, `.nets`, `.pl`,
`.scl`, and `.wts` files because the BBOPlace reader expects those filenames.

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
docker build -t frontiercs-bboplace-data:local /path/to/context
docker tag frontiercs-bboplace-data:local ghcr.io/frontiercs/frontiercs-bboplace-data:2026-06-ispd-iccad
python3 tools/bboplace/check_constants.py
python3 tools/bboplace/check_generated_tasks.py /path/to/generated/frontier-cs-2.0
```

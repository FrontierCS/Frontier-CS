# BBOPlace-Bench -> Harbor Adapter

This adapter generates Harbor-style tasks for BBOPlace-Bench. Each task wraps a
single `(benchmark, placer)` pair and exposes an iterative black-box evaluator
to the agent.

The agent writes `/app/solution.py` and can run:

```bash
python3 /app/submit.py --info
bash /app/submit.sh
```

`solution.py` may define `solve(info)`, `generate(info)`, `CANDIDATES`, or
`CANDIDATE`. The value should be one candidate vector or a list of candidate
vectors. The evaluator minimizes HPWL and reports Harbor reward as:

```text
reward = 1 / (1 + hpwl / 1e5)
```

The final verifier evaluates `/app/solution.py` and compares it with the best
successful iterative submission recorded in `/logs/agent/submissions.jsonl`.
The reported reward is the better of those two.

## Generate Tasks

From the repository root:

```bash
PYTHONPATH=adapters/bboplace-bench/src \
python3 -m bboplace_bench_harbor.main \
  --source bboplace \
  --output-dir datasets/bboplace-bench \
  --benchmarks adaptec1 \
  --placers mgo \
  --overwrite
```

BBOPlace-Bench requires external benchmark data before task generation. For
this Frontier-CS checkout, download the original datasets linked from
`bboplace/README.md`, extract them, and place them under:

```text
bboplace/benchmarks/
  ispd2005/
    adaptec1/
    adaptec2/
    ...
  iccad2015/
    superblue1/
    superblue3/
    ...
```

Generate tasks only after the needed benchmark directory exists. The generator
copies the selected benchmark into the Harbor judge image. During a trial, the
agent does not download benchmark files and does not receive direct benchmark
access; it should use:

```bash
python3 /app/submit.py --info
bash /app/submit.sh
```

If you are only inspecting the generated Harbor shape before downloading data,
add:

```bash
--allow-missing-benchmark
```

Tasks generated without benchmark data are structural only and will not run
until regenerated with the data present.

## Run with Harbor

```bash
uv run harbor trial start -p datasets/bboplace-bench/bboplace-bench-mgo-adaptec1-mp
```

The generated task uses two services:

- `main`: the agent workspace with `/app/submit.sh`, `/app/submit.py`, and
  static task metadata only. It does not contain the BBOPlace repository,
  benchmark data, or evaluator runtime.
- `judge`: a black-box HTTP evaluator that owns the BBOPlace repository and
  benchmark data. The agent submits candidate vectors to this service; the
  judge does not execute agent Python code.

The final verifier reads judge-recorded submissions from the judge HTTP API and
uses the best successful iterative submission. It does not execute
`/app/solution.py` inside an environment that contains the BBOPlace repository
or benchmark data.

## Current Scope

The default supported mode is `eval_gp_hpwl=False` with `mgo` or `sp`. `hpo` and
global-placement HPWL import DREAMPlace at runtime, so they require a
DREAMPlace-enabled Docker image and local benchmark data.

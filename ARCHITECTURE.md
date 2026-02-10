# Evaluation Architecture

This document describes how evaluation flows through the codebase and the
design choices behind the current structure.

## Audience

- **Problem contributors** (see `CONTRIBUTING.md`)
- **Model submitters** (see `SUBMIT.md`)
- **General researchers** using Frontier-CS to evaluate solutions

## Goals

- Clear separation between single-problem and batch evaluation.
- Shared validation and config parsing across research backends.
- Predictable cleanup to avoid orphaned cloud resources.
- Explicit naming to avoid backend ambiguity.

## Architecture at a Glance

- **CLI**:
  - `frontier eval` → `SingleEvaluator`
  - `frontier batch` → `BatchEvaluator`
  - `frontier list` / `frontier show` → problem discovery
- **CI**:
  - Validate Problems → `scripts/validate_problems.py` → `SingleEvaluator`
  - Weekly Batch Evaluation → `scripts/run_eval.sh` → `BatchEvaluator`

## Components

### SingleEvaluator
Unified API for **single-problem evaluation**:

- Selects a runner based on track and backend.
- Registers SIGINT/atexit hooks to tear down SkyPilot clusters on exit.

### BatchEvaluator
Orchestrates **batch evaluation** with parallel workers and SkyPilot
cluster pools:

- Work queues with resumable state and result aggregation.
- Resource-grouped cluster pools — pairs are grouped by
  `ResourceSignature` (cloud, accelerators, instance type) so that
  CPU-only and GPU problems run on separate pools.
- Hash-based resume — each result stores solution/problem hashes so stale
  results are automatically re-evaluated when source changes.

### Runners
Runners execute evaluation. The class hierarchy:

```
Runner (ABC)
├── ResearchRunner              # shared: problem validation, config loading, uv install
│   ├── ResearchDockerRunner    # local container
│   └── ResearchSkyPilotRunner  # cloud via SkyPilot
├── AlgorithmicLocalRunner      # go-judge via HTTP
└── AlgorithmicSkyPilotRunner   # go-judge on SkyPilot
```

### Solution Generation (`gen/`)
The `gen/` module generates solutions by calling LLMs. It is independent of
the evaluation pipeline — `frontier eval` and `frontier batch` do not
depend on it. It provides an LLM interface, an API key pool for concurrent
requests, and solution file formatting.

## Design Decisions

- **Single vs Batch**: `SingleEvaluator` stays focused on one-off runs
  (simple API + cleanup hooks), while `BatchEvaluator` owns scheduling,
  resumable state, and cluster pools. This keeps single-run paths
  lightweight and batch runs scalable.
- **Shared research helpers**: input validation and config parsing live in
  the `ResearchRunner` base class so Docker and SkyPilot backends stay in
  sync.
- **Cleanup strategy**: research evaluations tear down clusters by default
  unless `keep_cluster` is set. `SingleEvaluator` cleans up via an
  active-cluster registry; `BatchEvaluator` manages its own pool lifecycle.
- **Naming**: runner class names encode track + backend
  (e.g., `ResearchDockerRunner`) to remove ambiguity in logs and docs.
- **Score semantics**: a score of **0** can mean the evaluator ran
  successfully; failures are reported via status/metadata rather than score
  alone.
- **Reference solutions**: problems ship with `reference.cpp`/`reference.py`
  so CI can verify end-to-end evaluation without model submissions.
- **Results separation**: evaluation outputs go to a dedicated results
  repository to keep the main repo lean and auditable.
- **Internal vs public**: internal test cases and tooling live in a private
  repo; public artifacts are kept minimal but compatible.
- **Weekly vs local**: weekly CI uses `scripts/run_eval.sh` with batch
  scheduling; local runs use the same script or `frontier eval` for quick
  iteration.
- **Resource-grouped cluster pools**: `BatchEvaluator` groups pairs by
  `ResourceSignature` (cloud × accelerators × instance type) and creates a
  separate pool per group, avoiding the waste of running CPU-only problems
  on GPU clusters.
- **Hash-based resume**: resuming a batch compares solution/problem hashes
  against stored results. Changed inputs are re-evaluated even when a prior
  result exists, preventing silently stale scores.
- **Generation vs evaluation**: solution generation (`gen/`) is fully
  decoupled from evaluation. Generated files are plain source files with no
  special metadata; the evaluator has no dependency on the generation
  pipeline.

## Runner Flow (Research)

Both research runners share the same pre-evaluation steps (via
`ResearchRunner`):

1. Validate solution file and `.FAILED` marker.
2. Verify the problem path exists.
3. Load `config.yaml` and runtime settings.
4. Build uv install command if `uv_project` is specified.

Execution diverges at the backend:

- **Docker** — launches a local container.
- **SkyPilot** — provisions a cloud VM and runs remotely.

## Operations (Cleanup + CI)

- **Cleanup**: research evaluations tear down clusters by default unless
  `keep_cluster=True`. `SingleEvaluator` uses an active-cluster registry to
  clean up on SIGINT/atexit; `BatchEvaluator` manages its own cluster pool
  lifecycle.

- **CI**: problem validation runs single evals; the weekly batch job runs
  full evaluations on SkyPilot (typically GCP).

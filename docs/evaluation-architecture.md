# Evaluation Architecture

This document summarizes how evaluation flows through the codebase and names the
key components introduced in the recent refactors.

## Components

### SingleEvaluator
`SingleEvaluator` is the unified API for **single-problem evaluation**. It:

- Chooses a runner based on track and backend.
- Registers cleanup hooks for SkyPilot clusters (SIGINT/atexit).

### BatchEvaluator
`BatchEvaluator` orchestrates **batch evaluation** with parallel workers and
SkyPilot cluster pools. It handles:

- Work queues, resumable state, and result aggregation.
- Cluster pool lifecycle (create/cleanup).

### Runners
Runners execute the actual evaluation. The mapping is:

- **Research + docker** → `ResearchDockerRunner`
- **Research + skypilot** → `ResearchSkyPilotRunner`
- **Algorithmic + docker** → `AlgorithmicLocalRunner`
- **Algorithmic + skypilot** → `AlgorithmicSkyPilotRunner`

## Design Decisions

- **Single vs Batch**: `SingleEvaluator` stays focused on one-off evaluation
  (simple API + cleanup hooks), while `BatchEvaluator` owns scheduling,
  resumable state, and cluster pools. This keeps single-run paths lightweight
  and batch runs scalable.
- **Shared research helpers**: input validation and config parsing are shared
  in `ResearchRunner` to avoid drift between Docker and SkyPilot backends.
- **Cleanup strategy**: research SkyPilot evaluations down clusters by default
  (cost/safety), with `keep_cluster` as the opt-out. Batch uses its own pool
  cleanup because cluster lifecycle is managed at the scheduler level.
- **Naming**: runner class names are explicit about track + backend
  (e.g., `ResearchDockerRunner`) to remove ambiguity in logs and docs.

## Runner Flow (Research)

Both research runners share the same input validation and config parsing:

- Validate solution file and `.FAILED` marker.
- Ensure problem path exists.
- Load `config.yaml` and runtime settings.
- Build uv install command if `uv_project` is provided.

The execution path diverges only at the backend:

- Docker runner launches a local container.
- SkyPilot runner provisions and executes on cloud resources.

## Cleanup Behavior

- `ResearchSkyPilotRunner` always downs the evaluation cluster unless
  `keep_cluster=True`.
- Active clusters are tracked in a registry so `SingleEvaluator` can clean up on
  SIGINT/atexit.
- `BatchEvaluator` uses its own cluster pool cleanup (independent of the
  registry).

## CI Mapping

- **Validate Problems** uses `SingleEvaluator` through
  `scripts/validate_problems.py`.
- **Weekly Batch Evaluation** uses `BatchEvaluator` via `scripts/run_eval.sh`
  and typically runs on SkyPilot (GCP by default).

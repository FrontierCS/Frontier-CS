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


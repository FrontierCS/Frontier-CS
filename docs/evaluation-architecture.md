# Evaluation Architecture

This document summarizes how evaluation flows through the codebase, who it is
for, and the guiding design choices behind the current structure.

## Audience

- Contributors changing evaluation behavior, runners, or CI workflows.
- Maintainers debugging evaluation failures or infra cleanup issues.

## Goals

- Clear separation between single-problem and batch evaluation.
- Shared validation/config parsing across research backends.
- Predictable cleanup to avoid orphaned cloud resources.
- Explicit naming to avoid backend ambiguity.

## Architecture at a Glance

- **CLI**:
  - `frontier eval` → `SingleEvaluator`
  - `frontier batch` → `BatchEvaluator`
- **CI**:
  - Validate Problems → `scripts/validate_problems.py` → `SingleEvaluator`
  - Weekly Batch Evaluation → `scripts/run_eval.sh` → `BatchEvaluator`

## Components

### SingleEvaluator
Unified API for **single-problem evaluation**. It:

- Chooses a runner based on track and backend.
- Registers cleanup hooks for SkyPilot clusters (SIGINT/atexit).

### BatchEvaluator
Orchestrates **batch evaluation** with parallel workers and
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
- **Cleanup strategy**: research evaluations down clusters by default unless
  `keep_cluster` is set; batch handles its own pool cleanup.
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

## Operations (Cleanup + CI)

- **Cleanup**: research evaluations down clusters by default unless
  `keep_cluster=True`; `SingleEvaluator` also cleans up on SIGINT/atexit using an
  active-cluster registry. `BatchEvaluator` owns its cluster pool lifecycle.

- **CI**: Validate Problems runs single evals; Weekly Batch Evaluation runs
  batch evals (typically SkyPilot on GCP).

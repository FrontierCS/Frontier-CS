# Frontier-CS 2.0 -> Harbor Adapter

This adapter converts the Frontier-CS `2.0` track into Harbor task format.
It follows the structure used by Harbor's official
`frontier-cs-algorithm` adapter: each source problem becomes one Harbor task
with `task.toml`, `instruction.md`, `environment/`, `solution/`, and `tests/`.
The generated dataset is intended to be consumed directly by Harbor's CLI/API
for evaluating arbitrary agents on Frontier-CS 2.0.

## Generate Tasks

From the adapter directory:

```bash
uv run frontier-cs-2-0 \
  --source ../.. \
  --output-dir ../../datasets/frontier-cs-2.0 \
  --overwrite
```

Generate only the Erdos unit distance task:

```bash
uv run frontier-cs-2-0 \
  --source ../.. \
  --output-dir ../../datasets/frontier-cs-2.0 \
  --task-ids erdos_unit_distance \
  --overwrite
```

Generate only the small Erdos demo task:

```bash
uv run frontier-cs-2-0 \
  --source ../.. \
  --output-dir ../../datasets/frontier-cs-2.0 \
  --task-ids erdos_demo \
  --overwrite
```

## Run with Harbor

```bash
uv run harbor run -p datasets/frontier-cs-2.0
uv run harbor trial start -p datasets/frontier-cs-2.0/frontier-cs-2-0-erdos-unit-distance
uv run harbor trial start -p datasets/frontier-cs-2.0/frontier-cs-2-0-erdos-demo
```

## Task Contract

The agent works in `/app` and must create `/app/solution.py` unless the task
declares a directory submission. A judge sidecar prepares the task evaluator
once per trial; both iterative submissions and the final verifier score
through that same sidecar. The final verifier writes a normalized reward in
`/logs/verifier/reward.txt`.

During the trial, the agent can call:

```bash
bash /app/submit.sh
```

This submits the current `/app/solution.py` to a black-box judge service,
prints the score and feedback, and records each attempt in
`/logs/agent/submissions.jsonl`. The evaluator source is not mounted into the
agent workspace. The judge owns the authoritative submission log at
`/logs/judge/submissions.jsonl`; the final verifier filters iterative agent
submissions into `/logs/verifier/submissions.jsonl` for process-reward
analysis. The reported reward is the maximum of the final submission score and
the best successful iterative submission, so a timed-out agent can keep its
best submitted solution.

Some Harbor CLI versions print the timeout/error summary before rewards; in
that case inspect `result.json`, `verifier/reward.json`, and
`verifier/evaluation_result.json` in the trial directory.

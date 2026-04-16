# Solutions Repo Separation

## Problem

Infra code (agent_interface.py, generate_solutions.py) and generated solutions (.cpp, .meta.json) live in the same repo. This causes:

- Can't freely rebase/restructure infra without worrying about losing uncommitted solutions
- Git diffs polluted by large generated files
- No traceability — can't tell which version of infra generated a given solution

## Decision

1. **Move solutions to `FrontierCS/Frontier-CS-Result`** (already exists for storing results).
2. **Add `infra_git_hash` to `.meta.json`** so each solution records which commit of this repo generated it.
3. **Keep existing naming**: `{model_prefix}.cpp`, `{model_prefix}_{variant}.cpp`. Indices (`_0`, `_1`, `_2`) remain multi-variant within a single run.
4. **Version via git commits** in the result repo. Re-running overwrites files, but commit before re-running to preserve history.

## meta.json additions

```json
{
  "model": "claude-sonnet-4-5-20250514",
  "cost_usd": 0.55,
  "time_seconds": 337,
  "turns": 59,
  "tokens_in": 125000,
  "tokens_out": 18000,
  "status": "success",
  "infra_git_hash": "f54d370b",
  "timestamp": "2026-04-15T14:30:22Z"
}
```

## What stays in this repo

- `src/frontier_cs/gen/` — generation and agent infra code
- `algorithmic/problems/` — problem definitions
- `algorithmic/judge/` — judge server

## What moves to Frontier-CS-Result

- `algorithmic/solutions/` — all generated solution files
- `algorithmic/AGENT_EVAL_RESULTS.md` — eval result summaries

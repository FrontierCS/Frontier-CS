# Experimental vLLM Serving-Optimization Images

This task needs two images, mirroring the duckdb-e2e split: a public **agent**
image and a private **judge** image. Both bundle a clean upstream vLLM checkout
and the shared `serving_eval` harness. Build them before running a local Harbor
trial:

```bash
bash 2.0/problems/vllm_llm_serving_optimization/docker/build_images.sh
```

Defaults:

```text
VLLM_REF=v0.11.0
AGENT_TAG=frontiercs/vllm-serving-optimization-agent:experimental-v0.11.0
JUDGE_TAG=frontiercs/vllm-serving-optimization-judge:experimental-v0.11.0
```

The agent image contains:

```text
/app/vllm                 # clean upstream vLLM (no continuum, no reference fix)
/opt/serving_eval         # shared harness, used by the async public test
/opt/vllm-baseline        # optional precomputed baseline cache
```

The judge image contains:

```text
/opt/vllm-clean           # clean upstream vLLM (build + baseline reference)
/opt/serving_eval         # shared harness, used by the evaluator
/opt/vllm-baseline        # baseline-metrics cache (filled on first measurement)
```

## Runtime requirements (important)

Unlike duckdb-e2e, this task does **not** run the model inside the container.
Both the agent public test and the judge serve `meta-llama/Llama-3.1-8B-Instruct`
on a **Modal L40S** built from the (patched) vLLM source. The containers
therefore need:

- `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` in the environment (Modal auth). Use a
  Modal service-user token for unattended runs.
- A Modal Secret named `huggingface-secret` containing `HF_TOKEN` with access to
  the gated Llama-3.1 weights (`modal secret create huggingface-secret HF_TOKEN=...`).
  The container also reads `HF_TOKEN` for the `datasets` download.
- The judge additionally needs a reachable Docker daemon (mounted socket or
  DinD) to run the SWE-bench per-instance testbeds for the final resolve-rate.
  When no daemon is reachable, the harness falls back to a local sandbox and the
  patch-validity accuracy proxy.

The Modal image build uses `VLLM_USE_PRECOMPILED=1`, so only vLLM's Python layer
is rebuilt from the submitted source (minutes, not a full CUDA compile). This is
why the patch policy is Python-only.

## Baseline cache

The judge measures the vanilla (clean-tree) baseline once per role and caches it
at `/opt/vllm-baseline/baseline_metrics.json`, keyed by role (`agent` / `final`).
Baseline and patched builds are never served simultaneously, so a single L40S is
sufficient per environment. To precompute and bake the baseline into the image
(recommended for faster trials), run the harness against the clean tree offline
and copy the resulting `baseline_metrics.json` into the image at that path.

## Smoke test

```bash
bash 2.0/problems/vllm_llm_serving_optimization/docker/smoke_images.sh
```

This checks that the clean vLLM checkout, the `serving_eval` package, and the
Modal/OpenAI/datasets (and, for the judge, swebench + docker) clients are
importable. It does not exercise Modal or a GPU.

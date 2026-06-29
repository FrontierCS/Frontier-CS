"""Configuration for the vLLM serving evaluation harness.

A single :class:`EvalSettings` is built from the task ``evaluation`` config block
(passed in from the evaluator) with environment-variable fallbacks. The same
settings drive the judge-side measurement and the agent-side public test.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


@dataclass
class EvalSettings:
    model: str = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    gpu: str = "H100:2"  # Modal GPU spec; "H100:N" for N-way tensor parallel.
    dataset: str = "princeton-nlp/SWE-bench_Lite"
    dataset_split: str = "test"
    # Fixed seed for the deterministic random instance sample (SWE + BFCL).
    sample_seed: int = 20260624
    public_slice: str = "0:5"
    eval_slice: str = "0:50"
    arrival_mode: str = "jps"
    jps: float = 0.5
    workers: int = 8
    step_limit: int = 50
    temperature: float = 0.0
    max_completion_tokens: int = 2048
    accuracy_tolerance: float = 0.05  # relative-drop tolerance
    accuracy_abs_tolerance: float = 0.05  # absolute-drop tolerance (OR with relative)
    agent_accuracy_mode: str = "patch_validity"
    final_accuracy_mode: str = "resolve_rate"
    # Docker Hub namespace for prebuilt SWE-bench eval images (real resolve_rate).
    swebench_namespace: str = "swebench"
    correctness_smoke_prompts: int = 8
    # --- BFCL (function-calling) workload: the second judged workload, providing
    # a real, deterministic, non-zero accuracy + correctness signal. ---
    bfcl_public_slice: str = "0:8"
    bfcl_eval_slice: str = "0:40"
    bfcl_max_tokens: int = 768  # memory answers + tool args are longer than AST calls
    memory_max_steps: int = 20  # agentic step cap per memory instance (upstream MAXIMUM_STEP_LIMIT)
    # BFCL memory arrives as a seeded Poisson process. It uses its OWN rate
    # (bfcl_jps), higher than the SWE `jps`, because memory requests are short
    # (~5K ctx, 768 decode) and only pile up into real KV contention at a high
    # arrival rate. bfcl_workers only caps the fallback burst path (arrival != jps).
    bfcl_jps: float = 5.0
    bfcl_workers: int = 64
    # Final score blend over the two workloads (must sum to 1.0).
    swebench_weight: float = 0.5
    bfcl_weight: float = 0.5
    # Per-instance speedup is clamped to [1/cap, cap] so a single early-exiting or
    # erroring instance (tiny latency) cannot inflate the geomean, and a single
    # stall cannot tank it beyond the cap.
    max_per_instance_speedup: float = 8.0
    # BFCL per-sample greedy gate: at temperature 0 the patched run should reproduce
    # the baseline's per-instance correctness. Allowed correct@baseline ->
    # wrong@patched flips = max(bfcl_max_correctness_regressions floor, 5% of all
    # instances [absolute], 5% of the baseline-correct set [relative]). The 5%
    # abs-OR-rel band absorbs the batch-numerics non-determinism that flips many
    # instances run-to-run even between identical builds under concurrency.
    bfcl_max_correctness_regressions: int = 1
    bfcl_correctness_abs_tolerance: float = 0.05  # of all BFCL instances
    bfcl_correctness_tolerance: float = 0.05      # of the baseline-correct count
    modal_scaledown_seconds: int = 900
    modal_startup_timeout_seconds: int = 1200
    modal_deploy_retries: int = 3
    server_health_timeout_seconds: int = 1800
    build_timeout_seconds: int = 7200
    instance_timeout_seconds: int = 1200
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> "EvalSettings":
        config = dict(config or {})
        return cls(
            model=str(config.get("model", cls.model)),
            gpu=str(config.get("gpu", cls.gpu)),
            dataset=str(config.get("dataset", cls.dataset)),
            dataset_split=str(config.get("dataset_split", cls.dataset_split)),
            sample_seed=_as_int(config.get("sample_seed"), cls.sample_seed),
            public_slice=str(config.get("public_slice", cls.public_slice)),
            eval_slice=str(config.get("eval_slice", cls.eval_slice)),
            arrival_mode=str(config.get("arrival_mode", cls.arrival_mode)),
            jps=_as_float(config.get("jps"), cls.jps),
            workers=_as_int(config.get("workers"), cls.workers),
            step_limit=_as_int(config.get("step_limit"), cls.step_limit),
            temperature=_as_float(config.get("temperature"), cls.temperature),
            max_completion_tokens=_as_int(config.get("max_completion_tokens"), cls.max_completion_tokens),
            accuracy_tolerance=_as_float(config.get("accuracy_tolerance"), cls.accuracy_tolerance),
            accuracy_abs_tolerance=_as_float(config.get("accuracy_abs_tolerance"), cls.accuracy_abs_tolerance),
            agent_accuracy_mode=str(config.get("agent_accuracy_mode", cls.agent_accuracy_mode)),
            final_accuracy_mode=str(config.get("final_accuracy_mode", cls.final_accuracy_mode)),
            swebench_namespace=str(config.get("swebench_namespace", cls.swebench_namespace)),
            correctness_smoke_prompts=_as_int(
                config.get("correctness_smoke_prompts"), cls.correctness_smoke_prompts
            ),
            bfcl_public_slice=str(config.get("bfcl_public_slice", cls.bfcl_public_slice)),
            bfcl_eval_slice=str(config.get("bfcl_eval_slice", cls.bfcl_eval_slice)),
            bfcl_max_tokens=_as_int(config.get("bfcl_max_tokens"), cls.bfcl_max_tokens),
            memory_max_steps=_as_int(config.get("memory_max_steps"), cls.memory_max_steps),
            bfcl_jps=_as_float(config.get("bfcl_jps"), cls.bfcl_jps),
            bfcl_workers=_as_int(config.get("bfcl_workers"), cls.bfcl_workers),
            swebench_weight=_as_float(config.get("swebench_weight"), cls.swebench_weight),
            bfcl_weight=_as_float(config.get("bfcl_weight"), cls.bfcl_weight),
            max_per_instance_speedup=_as_float(
                config.get("max_per_instance_speedup"), cls.max_per_instance_speedup
            ),
            bfcl_max_correctness_regressions=_as_int(
                config.get("bfcl_max_correctness_regressions"), cls.bfcl_max_correctness_regressions
            ),
            bfcl_correctness_abs_tolerance=_as_float(
                config.get("bfcl_correctness_abs_tolerance"), cls.bfcl_correctness_abs_tolerance
            ),
            bfcl_correctness_tolerance=_as_float(
                config.get("bfcl_correctness_tolerance"), cls.bfcl_correctness_tolerance
            ),
            modal_scaledown_seconds=_as_int(config.get("modal_scaledown_seconds"), cls.modal_scaledown_seconds),
            modal_deploy_retries=_as_int(config.get("modal_deploy_retries"), cls.modal_deploy_retries),
            modal_startup_timeout_seconds=_as_int(
                config.get("modal_startup_timeout_seconds"), cls.modal_startup_timeout_seconds
            ),
            server_health_timeout_seconds=_as_int(
                config.get("server_health_timeout_seconds"), cls.server_health_timeout_seconds
            ),
            build_timeout_seconds=_as_int(config.get("build_timeout_seconds"), cls.build_timeout_seconds),
            instance_timeout_seconds=_as_int(config.get("instance_timeout_seconds"), cls.instance_timeout_seconds),
            extra=config,
        )

    def slice_for_role(self, role: str) -> str:
        return self.eval_slice if role == "final" else self.public_slice

    def bfcl_slice_for_role(self, role: str) -> str:
        return self.bfcl_eval_slice if role == "final" else self.bfcl_public_slice

    def accuracy_mode_for_role(self, role: str) -> str:
        return self.final_accuracy_mode if role == "final" else self.agent_accuracy_mode

    def workload_weights(self) -> tuple[float, float]:
        """Return normalized (swebench_weight, bfcl_weight) summing to 1.0."""
        sw = max(0.0, self.swebench_weight)
        bf = max(0.0, self.bfcl_weight)
        total = sw + bf
        if total <= 0:
            return 0.5, 0.5
        return sw / total, bf / total


def parse_slice(spec: str, length: int) -> range:
    """Parse a ``start:stop`` slice spec into a concrete index range."""
    spec = (spec or "").strip()
    if not spec:
        return range(length)
    parts = spec.split(":")
    try:
        start = int(parts[0]) if parts[0] else 0
        stop = int(parts[1]) if len(parts) > 1 and parts[1] else length
    except ValueError:
        return range(length)
    start = max(0, min(start, length))
    stop = max(start, min(stop, length))
    return range(start, stop)


def modal_available() -> bool:
    return bool(os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"))

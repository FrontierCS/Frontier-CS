"""Orchestration: build, serve, and measure baseline vs patched vLLM.

Two workloads are run against each served build and scored independently, then
blended 50/50 by the evaluator:

* **SWE-bench** — a multi-turn, long-shared-prefix agentic run. Drives the
  latency signal; gated on greedy-output correctness vs the baseline.
* **BFCL** — single-turn function-calling queries with a real, deterministic,
  non-zero AST-checked accuracy. Provides a *live* accuracy guardrail (unlike
  SWE-bench resolve rate, which is ~0 for an 8B model) and a per-sample
  correctness gate that catches generation corruption.

To honour the one-H100-per-environment budget, the baseline and the patched
build are never served at the same time. The baseline is read from a cache when
available; otherwise it is measured once (serving the clean tree) and cached. The
patched build is then served on its own, gated on correctness against the cached
baseline outputs, and measured under the identical workloads.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from . import bfcl
from .accuracy import compute_accuracy
from .agent_runner import InstanceResult, run_workload
from .correctness import collect_greedy_outputs, compare_outputs
from .sandbox import docker_available
from .serving import ServerHandle, ServingError, deploy_server, stop_server, wait_healthy
from .settings import EvalSettings

# Patched instances whose request actually failed (tiny latency) — excluded from
# the speedup numerator / penalized so "fail fast" never reads as a speedup.
_SWE_FAILED_STATUSES = {"api_error"}
_BFCL_FAILED_STATUSES = {"api_error"}


def _short_id() -> str:
    return uuid.uuid4().hex[:10]


def _latency_map(results: list[InstanceResult]) -> dict[str, float]:
    return {result.instance_id: result.latency_seconds for result in results}


def _swe_failed_ids(results: list[InstanceResult]) -> list[str]:
    return [r.instance_id for r in results if r.exit_status in _SWE_FAILED_STATUSES]


def _bfcl_failed_ids(results: list[bfcl.BfclResult]) -> list[str]:
    return [r.instance_id for r in results if r.exit_status in _BFCL_FAILED_STATUSES]


def _apply_patch(clean_source: str, patch_path: str) -> Path:
    tmp_root = Path(tempfile.mkdtemp(prefix="vllm-serving-opt-src-"))
    patched = tmp_root / "vllm"
    # Keep .git: vLLM's build uses setuptools_scm for versioning, and applying the
    # patch to a tracked tree leaves the changes in the working tree (an editable
    # install then picks them up). The patch is applied with `git apply` below.
    shutil.copytree(clean_source, patched, dirs_exist_ok=False)
    patch_text = Path(patch_path).read_text(encoding="utf-8", errors="replace")
    if patch_text.strip():
        check = subprocess.run(
            ["git", "apply", "--check", patch_path],
            cwd=str(patched),
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            shutil.rmtree(tmp_root, ignore_errors=True)
            raise ServingError("patch does not apply cleanly to the pinned vLLM source")
        subprocess.run(["git", "apply", patch_path], cwd=str(patched), check=True, capture_output=True, text=True)
    return patched


def _serve(src: str, settings: EvalSettings, *, app_name: str, label: str) -> ServerHandle:
    handle = deploy_server(
        src_path=src,
        model=settings.model,
        gpu=settings.gpu,
        app_name=app_name,
        label=label,
        scaledown_seconds=settings.modal_scaledown_seconds,
        startup_timeout_seconds=settings.modal_startup_timeout_seconds,
        build_timeout_seconds=settings.build_timeout_seconds,
        deploy_retries=settings.modal_deploy_retries,
    )
    wait_healthy(handle, model=settings.model, timeout_seconds=settings.server_health_timeout_seconds)
    return handle


def _measure_bfcl(handle: ServerHandle, settings: EvalSettings, *, role: str) -> dict[str, Any]:
    """Run the BFCL function-calling workload; real AST-checked accuracy."""
    if not bfcl.bfcl_available():
        return {"available": False, "per_instance_latency": {}, "accuracy": 0.0,
                "correctness_map": {}, "outputs": {}, "failed_ids": [], "n_instances": 0}
    results = bfcl.run_bfcl_workload(base_url=handle.base_url, settings=settings, role=role)
    return {
        "available": True,
        "per_instance_latency": bfcl.per_instance_latency(results),
        "accuracy": bfcl.accuracy(results),
        "correctness_map": bfcl.correctness_map(results),
        "outputs": bfcl.outputs(results),
        "failed_ids": _bfcl_failed_ids(results),
        "n_instances": len(results),
    }


def _measure_server(
    handle: ServerHandle,
    settings: EvalSettings,
    *,
    role: str,
    accuracy_mode: str,
    prefer_docker: bool,
    greedy_n: int,
    run_id: str,
) -> dict[str, Any]:
    """Measure BOTH workloads against a served build (used for the baseline)."""
    greedy = collect_greedy_outputs(handle.base_url, settings=settings, n=greedy_n)
    results = run_workload(
        base_url=handle.base_url,
        settings=settings,
        role=role,
        prefer_docker=prefer_docker,
    )
    accuracy = compute_accuracy(results, settings=settings, mode=accuracy_mode, run_id=run_id)
    bfcl_measured = _measure_bfcl(handle, settings, role=role)
    return {
        "swebench": {
            "per_instance_latency": _latency_map(results),
            "accuracy": float(accuracy["accuracy"]),
            "accuracy_mode": accuracy["mode"],
            "accuracy_proxy_used": bool(accuracy["proxy_used"]),
            "greedy_outputs": greedy,
            "failed_ids": _swe_failed_ids(results),
            "n_instances": len(results),
        },
        "bfcl": bfcl_measured,
    }


def _load_baseline_cache(path: str, role: str) -> dict[str, Any] | None:
    cache_path = Path(path)
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    entry = payload.get(role)
    return entry if isinstance(entry, dict) else None


def _store_baseline_cache(path: str, role: str, entry: dict[str, Any]) -> None:
    cache_path = Path(path)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {}
        if cache_path.exists():
            existing = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                payload = existing
        payload[role] = entry
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass


def _baseline_has_data(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    swe = entry.get("swebench") or {}
    return bool(swe.get("per_instance_latency"))


def _get_baseline(
    clean_source: str,
    settings: EvalSettings,
    *,
    role: str,
    accuracy_mode: str,
    baseline_cache_path: str,
    prefer_docker: bool,
) -> dict[str, Any]:
    cached = _load_baseline_cache(baseline_cache_path, role)
    if _baseline_has_data(cached):
        return cached  # type: ignore[return-value]

    app_name = f"vllm-serv-opt-base-{role}-{_short_id()}"
    handle = _serve(clean_source, settings, app_name=app_name, label=app_name)
    try:
        measured = _measure_server(
            handle,
            settings,
            role=role,
            accuracy_mode=accuracy_mode,
            prefer_docker=prefer_docker,
            greedy_n=settings.correctness_smoke_prompts,
            run_id=f"baseline-{role}-{_short_id()}",
        )
    finally:
        stop_server(app_name)
    _store_baseline_cache(baseline_cache_path, role, measured)
    return measured


def _bfcl_correctness_ok(
    baseline_map: dict[str, bool],
    patched_map: dict[str, bool],
    *,
    max_regressions: int,
    abs_tolerance: float = 0.05,
    rel_tolerance: float = 0.05,
) -> tuple[bool, int]:
    """Per-sample greedy gate: a temperature-0 patch should not flip BFCL answers
    from correct (baseline) to wrong/undecodable (patched). Tolerates flips up to
    ``max(max_regressions, abs_tolerance * n_instances, rel_tolerance *
    n_baseline_correct)`` — a 5%/5% abs-OR-rel band that absorbs the batch-numerics
    non-determinism which flips many instances run-to-run (even between identical
    builds) under concurrency, while still catching a real correctness regression."""
    n = len(baseline_map)
    n_baseline_correct = sum(1 for v in baseline_map.values() if v)
    regressions = sum(
        1 for iid, b in baseline_map.items() if b and not patched_map.get(iid, False)
    )
    allowed = max(
        int(max_regressions),
        math.ceil(abs_tolerance * n),
        math.ceil(rel_tolerance * n_baseline_correct),
    )
    return regressions <= allowed, regressions


def run_measurement(
    *,
    patch_path: str,
    role: str,
    config: dict[str, Any] | None,
    clean_source: str,
    baseline_cache_path: str,
) -> dict[str, Any]:
    settings = EvalSettings.from_config(config)
    accuracy_mode = settings.accuracy_mode_for_role(role)
    prefer_docker = (role == "final") and docker_available()
    info: dict[str, Any] = {
        "role": role,
        "accuracy_mode": accuracy_mode,
        "prefer_docker": prefer_docker,
        "bfcl_available": bfcl.bfcl_available(),
    }

    try:
        baseline = _get_baseline(
            clean_source,
            settings,
            role=role,
            accuracy_mode=accuracy_mode,
            baseline_cache_path=baseline_cache_path,
            prefer_docker=prefer_docker,
        )
    except ServingError as exc:
        return {"ok": False, "gate": f"baseline serving failed: {exc}", "info": info}

    base_swe = baseline.get("swebench", {}) or {}
    base_bfcl = baseline.get("bfcl", {}) or {}

    patched_src: Path | None = None
    app_name = f"vllm-serv-opt-patch-{role}-{_short_id()}"
    try:
        patched_src = _apply_patch(clean_source, patch_path)
    except ServingError as exc:
        return {"ok": False, "gate": str(exc), "info": info}

    handle: ServerHandle | None = None
    try:
        try:
            handle = _serve(str(patched_src), settings, app_name=app_name, label=app_name)
        except ServingError as exc:
            return {"ok": False, "gate": f"patched build/serve failed: {exc}", "info": info}

        # --- SWE-bench greedy correctness gate ---
        patched_greedy = collect_greedy_outputs(
            handle.base_url, settings=settings, n=settings.correctness_smoke_prompts
        )
        correctness_ok, mismatches = compare_outputs(
            base_swe.get("greedy_outputs", {}), patched_greedy
        )
        info["greedy_mismatches"] = mismatches

        # --- SWE-bench workload (latency + proxy accuracy) ---
        swe_results = run_workload(
            base_url=handle.base_url, settings=settings, role=role, prefer_docker=prefer_docker
        )
        swe_patched_accuracy = compute_accuracy(
            swe_results, settings=settings, mode=accuracy_mode, run_id=f"patched-{role}-{_short_id()}"
        )
        info["baseline_accuracy_mode"] = base_swe.get("accuracy_mode")
        info["patched_accuracy_proxy_used"] = bool(swe_patched_accuracy["proxy_used"])
        info["swe_instances"] = len(swe_results)

        # --- BFCL workload (real AST accuracy + per-sample correctness gate) ---
        bfcl_patched = _measure_bfcl(handle, settings, role=role)
        info["bfcl_instances"] = bfcl_patched.get("n_instances", 0)
        info["bfcl_patched_accuracy"] = bfcl_patched.get("accuracy", 0.0)

        bfcl_correctness_ok = True
        bfcl_regressions = 0
        if base_bfcl.get("available") and bfcl_patched.get("available"):
            bfcl_correctness_ok, bfcl_regressions = _bfcl_correctness_ok(
                base_bfcl.get("correctness_map", {}),
                bfcl_patched.get("correctness_map", {}),
                max_regressions=settings.bfcl_max_correctness_regressions,
                abs_tolerance=settings.bfcl_correctness_abs_tolerance,
                rel_tolerance=settings.bfcl_correctness_tolerance,
            )
        info["bfcl_correctness_regressions"] = bfcl_regressions

        return {
            "ok": True,
            "correctness_ok": correctness_ok,
            "bfcl_correctness_ok": bfcl_correctness_ok,
            "info": info,
            "swebench": {
                "baseline": {
                    "per_instance_latency": base_swe.get("per_instance_latency", {}),
                    "accuracy": float(base_swe.get("accuracy", 0.0)),
                },
                "patched": {
                    "per_instance_latency": _latency_map(swe_results),
                    "accuracy": float(swe_patched_accuracy["accuracy"]),
                    "failed_ids": _swe_failed_ids(swe_results),
                },
            },
            "bfcl": {
                "available": bool(base_bfcl.get("available") and bfcl_patched.get("available")),
                "baseline": {
                    "per_instance_latency": base_bfcl.get("per_instance_latency", {}),
                    "accuracy": float(base_bfcl.get("accuracy", 0.0)),
                },
                "patched": {
                    "per_instance_latency": bfcl_patched.get("per_instance_latency", {}),
                    "accuracy": float(bfcl_patched.get("accuracy", 0.0)),
                    "failed_ids": bfcl_patched.get("failed_ids", []),
                },
            },
        }
    finally:
        if handle is not None:
            stop_server(app_name)
        if patched_src is not None:
            shutil.rmtree(patched_src.parent, ignore_errors=True)


def run_public_test(
    *,
    src: str,
    config: dict[str, Any] | None,
    baseline_cache_path: str,
) -> dict[str, Any]:
    """Agent-facing public test: serve the working tree and report feedback."""
    from .scoring import provisional_score

    settings = EvalSettings.from_config(config)
    role = "agent"
    accuracy_mode = settings.accuracy_mode_for_role(role)
    prefer_docker = docker_available()
    app_name = f"vllm-serv-opt-public-{_short_id()}"

    handle: ServerHandle | None = None
    try:
        handle = _serve(src, settings, app_name=app_name, label=app_name)
        measured = _measure_server(
            handle,
            settings,
            role=role,
            accuracy_mode=accuracy_mode,
            prefer_docker=prefer_docker,
            greedy_n=settings.correctness_smoke_prompts,
            run_id=f"public-{_short_id()}",
        )
    except ServingError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        if handle is not None:
            stop_server(app_name)

    swe = measured.get("swebench", {})
    bfcl_m = measured.get("bfcl", {})
    patched_swe_latency = swe.get("per_instance_latency", {})
    result: dict[str, Any] = {
        "ok": True,
        "swe_instances": swe.get("n_instances", 0),
        "swe_accuracy": swe.get("accuracy", 0.0),
        "bfcl_instances": bfcl_m.get("n_instances", 0),
        "bfcl_accuracy": bfcl_m.get("accuracy", 0.0),
        "swe_mean_latency_seconds": (
            sum(patched_swe_latency.values()) / len(patched_swe_latency)
            if patched_swe_latency else 0.0
        ),
        "per_instance_latency": patched_swe_latency,
    }

    baseline = _load_baseline_cache(baseline_cache_path, role)
    if _baseline_has_data(baseline):
        base_swe = baseline.get("swebench", {})
        base_bfcl = baseline.get("bfcl", {})
        provisional = provisional_score(
            {str(k): float(v) for k, v in base_swe.get("per_instance_latency", {}).items()},
            {str(k): float(v) for k, v in patched_swe_latency.items()},
            float(base_swe.get("accuracy", 0.0)),
            float(swe.get("accuracy", 0.0)),
            settings.accuracy_tolerance,
            cap=settings.max_per_instance_speedup,
            abs_tolerance=settings.accuracy_abs_tolerance,
            baseline_bfcl_latency={str(k): float(v) for k, v in base_bfcl.get("per_instance_latency", {}).items()},
            patched_bfcl_latency={str(k): float(v) for k, v in bfcl_m.get("per_instance_latency", {}).items()},
            baseline_bfcl_accuracy=float(base_bfcl.get("accuracy", 0.0)),
            patched_bfcl_accuracy=float(bfcl_m.get("accuracy", 0.0)),
            weights=settings.workload_weights(),
        )
        result["provisional"] = provisional
    else:
        result["note"] = "no baseline cache present; reporting raw latency/accuracy only"
    return result

"""Accuracy signals for the workload.

Two modes, both comparable across baseline and patched runs:

* ``patch_validity`` (cheap, used for iterative public feedback): the fraction
  of instances that produced a non-empty, syntactically valid unified diff and
  reached a submit/limit-with-patch terminal state. For a pure serving/scheduler
  optimization this should be identical to the baseline; it cheaply catches
  patches that corrupt generation or truncate context.
* ``resolve_rate`` (faithful, used for final verification): the SWE-bench
  resolved fraction computed locally by the ``swebench`` harness (per-instance
  Docker test execution). Falls back to ``patch_validity`` if the harness is
  unavailable, flagging that the proxy was used.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .agent_runner import InstanceResult
from .settings import EvalSettings

_TERMINAL_WITH_WORK = {"submitted", "limit_with_patch"}


def _looks_like_diff(patch: str) -> bool:
    if not patch or not patch.strip():
        return False
    return ("diff --git" in patch) or ("--- " in patch and "+++ " in patch)


def patch_validity_rate(results: list[InstanceResult]) -> float:
    if not results:
        return 0.0
    valid = sum(
        1
        for result in results
        if result.exit_status in _TERMINAL_WITH_WORK and _looks_like_diff(result.patch)
    )
    return valid / len(results)


def build_predictions(results: list[InstanceResult], model: str) -> dict[str, dict[str, str]]:
    return {
        result.instance_id: {
            "model_name_or_path": model,
            "instance_id": result.instance_id,
            "model_patch": result.patch or "",
        }
        for result in results
    }


def resolve_rate(
    results: list[InstanceResult],
    *,
    settings: EvalSettings,
    run_id: str,
) -> tuple[float, bool]:
    """Return (accuracy, proxy_used). proxy_used=True if harness unavailable."""
    try:
        import swebench  # noqa: F401
    except Exception:
        return patch_validity_rate(results), True

    predictions = build_predictions(results, settings.model)
    instance_ids = [r.instance_id for r in results]
    with tempfile.TemporaryDirectory(prefix="vllm-serving-opt-acc-") as tmp:
        preds_path = Path(tmp) / "preds.json"
        preds_path.write_text(json.dumps(predictions), encoding="utf-8")
        try:
            import inspect

            from swebench.harness.run_evaluation import main as run_eval_main  # type: ignore
        except Exception:
            return patch_validity_rate(results), True

        # Pass values for every kwarg the installed harness accepts; swebench has
        # added required params over releases (namespace/modal/rewrite_reports in
        # 4.x). namespace pulls prebuilt eval images from Docker Hub (no local
        # image build) and modal=False runs them via the local Docker daemon.
        all_kwargs: dict[str, Any] = {
            "dataset_name": settings.dataset,
            "split": settings.dataset_split,
            "instance_ids": instance_ids,
            "predictions_path": str(preds_path),
            "max_workers": max(1, settings.workers),
            "run_id": run_id,
            "timeout": settings.instance_timeout_seconds,
            "cache_level": "env",
            "clean": False,
            "force_rebuild": False,
            "open_file_limit": 4096,
            "report_dir": tmp,
            "namespace": settings.swebench_namespace,
            "rewrite_reports": False,
            "modal": False,
            "instance_image_tag": "latest",
            "env_image_tag": "latest",
        }
        try:
            params = inspect.signature(run_eval_main).parameters
        except (TypeError, ValueError):
            return patch_validity_rate(results), True
        call_kwargs = {k: v for k, v in all_kwargs.items() if k in params}
        # If the harness declares a required param we do not recognise, fall back
        # rather than risk a misleading score from a signature mismatch.
        missing_required = [
            name
            for name, p in params.items()
            if p.default is inspect._empty and name not in call_kwargs
        ]
        if missing_required:
            return patch_validity_rate(results), True

        # swebench writes its summary report (<model>.<run_id>.json) and logs to
        # the process CWD, so run it with CWD pinned to our temp dir to collect
        # everything in one place for _read_resolved_count.
        prev_cwd = os.getcwd()
        try:
            os.chdir(tmp)
            run_eval_main(**call_kwargs)
        except Exception:
            return patch_validity_rate(results), True
        finally:
            try:
                os.chdir(prev_cwd)
            except Exception:
                pass

        resolved = _read_resolved_count(Path(tmp), settings.model)
        if resolved is None:
            return patch_validity_rate(results), True
        total = max(1, len(results))
        return resolved / total, False


def _read_resolved_count(report_dir: Path, model: str) -> int | None:
    candidates = list(report_dir.glob("*.json")) + list(report_dir.glob("**/*report*.json"))
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        for key in ("resolved_instances", "resolved"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, list):
                return len(value)
    return None


def compute_accuracy(
    results: list[InstanceResult],
    *,
    settings: EvalSettings,
    mode: str,
    run_id: str,
) -> dict[str, Any]:
    if mode == "resolve_rate":
        accuracy, proxy_used = resolve_rate(results, settings=settings, run_id=run_id)
        return {"accuracy": accuracy, "mode": "resolve_rate", "proxy_used": proxy_used}
    return {"accuracy": patch_validity_rate(results), "mode": "patch_validity", "proxy_used": False}

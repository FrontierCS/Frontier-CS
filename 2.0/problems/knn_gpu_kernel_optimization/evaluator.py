"""Evaluator for the brute-force k-NN GPU kernel-optimization task.

The agent submits a unified diff over the ``knnlib`` Python package. The judge:

1. statically validates the patch against an allowlist (only ``knnlib/**`` may
   change; no ``flashlib``/cuML/network/env access; bounded size);
2. applies it to a pristine copy of ``knnlib`` baked into the judge image at
   ``/opt/knnlib-clean``;
3. runs an isolated worker subprocess that, for each hidden ``(Q, M, D, k)``
   workload, times the patched ``knnlib.knn`` against a *frozen* naive baseline
   (``/opt/knn_ref/refknn.py``) on identical seeded data and measures each
   result's recall@k against the exact top-k recomputed from that baseline;
4. gates on nearest-neighbour quality (agent recall@k must stay at or above a
   threshold vs the exact baseline) and scores by the geometric-mean speedup.

When the judge source tree is not present (e.g. local static checks on a box
without a GPU), the evaluator still validates the patch policy and returns a
smoke pass, so ``python3 evaluator.py reference.patch`` works anywhere.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_PATCH_BYTES = 1_000_000
MAX_CHANGED_FILES = 40
TASK_CONFIG_PATH = Path("/judge/task_config.json")

DEFAULT_CLEAN_SOURCE = Path("/opt/knnlib-clean")   # pristine package (patched here)
DEFAULT_BASELINE_SOURCE = Path("/opt/knn_ref")     # frozen naive baseline (refknn.py)


def _load_task_config() -> dict[str, Any]:
    try:
        payload = json.loads(TASK_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


TASK_CONFIG = _load_task_config()
EVALUATION_CONFIG = TASK_CONFIG.get("evaluation", {}) if isinstance(TASK_CONFIG.get("evaluation"), dict) else {}


def _cfg(name: str, default):
    return EVALUATION_CONFIG.get(name, default)


def _cfg_int(name: str, default: int) -> int:
    try:
        return int(EVALUATION_CONFIG.get(name, default))
    except Exception:
        return default


def _cfg_float(name: str, default: float) -> float:
    try:
        return float(EVALUATION_CONFIG.get(name, default))
    except Exception:
        return default


def _cfg_bool(name: str, default: bool) -> bool:
    raw = EVALUATION_CONFIG.get(name, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(raw)


WARMUP_ITERS = _cfg_int("warmup_iters", 3)
TIMED_ITERS = _cfg_int("timed_iters", 7)
RECALL_THRESHOLD = _cfg_float("recall_threshold", 0.99)   # agent recall@k >= threshold
SPEEDUP_TARGET = _cfg_float("speedup_target", 6.0)        # geomean speedup mapped to full score
WORKER_TIMEOUT_SECONDS = _cfg_int("worker_timeout_seconds", 3600)
BASE_SEED = _cfg_int("base_seed", 20260701)

# Editable surface: only the shipped package.
ALLOWED_PATTERNS = (
    "knnlib/**",
)
# Never touchable, even though they are not shipped in the agent workspace.
DENIED_PATTERNS = (
    "evaluator.py",
    "reference.patch",
    "refknn.py",
    "**/refknn.py",
    "**/conftest.py",
    "**/test_*.py",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
)
# Forbidden substrings in added lines (defense in depth). The agent must write
# its own kernels, not call an external optimized library, read the
# environment, spawn processes, or touch the network.
FORBIDDEN_TOKENS = (
    "flashlib",
    "cuml",
    "cudf",
    "cupy",
    "faiss",
    "sklearn",
    "scikit",
    "os.environ",
    "getenv",
    "putenv",
    "setenv",
    "subprocess",
    "socket",
    "urllib",
    "requests",
    "importlib.import_module",
    "__import__",
)


@dataclass(frozen=True)
class PatchFile:
    old_path: str
    new_path: str
    added_lines: tuple[str, ...]
    removed_lines: tuple[str, ...]

    @property
    def path(self) -> str:
        return self.new_path if self.new_path != "/dev/null" else self.old_path


def _match(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _invalid(message: str, metrics: dict[str, Any] | None = None):
    payload = metrics or {}
    payload.setdefault("valid_patch", 0)
    return 0.0, 0.0, message, payload


def _parse_patch(text: str) -> list[PatchFile]:
    files: list[PatchFile] = []
    current_old = ""
    current_new = ""
    added: list[str] = []
    removed: list[str] = []
    in_file = False

    for line in text.splitlines():
        if line.startswith("diff --git "):
            if in_file:
                files.append(PatchFile(current_old, current_new, tuple(added), tuple(removed)))
            in_file = True
            current_old = current_new = ""
            added = []
            removed = []
            continue
        if not in_file:
            continue
        if line.startswith("--- "):
            current_old = line[4:].strip()
            if current_old.startswith("a/"):
                current_old = current_old[2:]
            continue
        if line.startswith("+++ "):
            current_new = line[4:].strip()
            if current_new.startswith("b/"):
                current_new = current_new[2:]
            continue
        if line.startswith("+") and not line.startswith("+++ "):
            added.append(line[1:])
            continue
        if line.startswith("-") and not line.startswith("--- "):
            removed.append(line[1:])

    if in_file:
        files.append(PatchFile(current_old, current_new, tuple(added), tuple(removed)))
    return files


def _validate_path(path: str) -> tuple[bool, str]:
    if not path or path == "/dev/null":
        return True, ""
    if path.startswith("/") or ".." in Path(path).parts:
        return False, f"unsafe patch path: {path}"
    if _match(path, DENIED_PATTERNS):
        return False, f"changed file is outside task boundary: {path}"
    if not _match(path, ALLOWED_PATTERNS):
        return False, f"changed file is not allowlisted (only knnlib/** may change): {path}"
    if not path.endswith(".py"):
        return False, f"only Python files may change: {path}"
    return True, ""


def validate_patch(patch_path: Path) -> tuple[bool, str, dict[str, Any]]:
    if not patch_path.exists():
        return False, "solution patch does not exist", {}
    size = patch_path.stat().st_size
    if size > MAX_PATCH_BYTES:
        return False, f"patch is too large ({size} bytes > {MAX_PATCH_BYTES})", {}
    text = patch_path.read_text(encoding="utf-8", errors="replace")
    patch_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    files = _parse_patch(text)
    metrics: dict[str, Any] = {
        "patch_bytes": size,
        "patch_sha256": patch_hash,
        "changed_files": len(files),
    }
    if len(files) > MAX_CHANGED_FILES:
        return False, f"too many changed files ({len(files)} > {MAX_CHANGED_FILES})", metrics

    for patch_file in files:
        path = patch_file.path
        if patch_file.new_path == "/dev/null":
            return False, f"deleting files is outside task boundary: {patch_file.old_path}", metrics
        if patch_file.old_path != "/dev/null" and patch_file.old_path != patch_file.new_path:
            ok, err = _validate_path(patch_file.old_path)
            if not ok:
                return False, f"rename/copy source is outside task boundary: {err}", metrics
        ok, err = _validate_path(path)
        if not ok:
            return False, err, metrics
        added_text = "\n".join(patch_file.added_lines)
        low = added_text.lower()
        for token in FORBIDDEN_TOKENS:
            if token in low:
                return False, f"{path}: forbidden token in added code ({token})", metrics

    metrics["valid_patch"] = 1
    return True, "patch accepted by static policy", metrics


def clean_env(tmp_root: Path) -> dict[str, str]:
    home = tmp_root / "home"
    tmp = tmp_root / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "LC_ALL": "C",
        "LANG": "C",
    }
    for key in ("CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "LD_LIBRARY_PATH",
                "TRITON_CACHE_DIR", "CUDA_HOME"):
        if key in os.environ:
            env[key] = os.environ[key]
    env.setdefault("TRITON_CACHE_DIR", str(tmp_root / "triton_cache"))
    return env


def run_checked(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), env=env, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True,
    )


def sanitize_error_text(text: str) -> str:
    text = re.sub(r"/tmp/[A-Za-z0-9_./-]+", "<tmp>", text)
    text = re.sub(r"/opt/[A-Za-z0-9_./-]+", "<judge>", text)
    text = re.sub(r"M=\d+", "M=<hidden>", text)
    text = re.sub(r"Q=\d+", "Q=<hidden>", text)
    text = re.sub(r"seed[=:]?\s*\d+", "seed=<hidden>", text, flags=re.IGNORECASE)
    return text[-600:]


def geometric_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.exp(sum(math.log(max(v, 1e-9)) for v in values) / len(values))


def score_from_speedup(gm_speedup: float) -> float:
    if gm_speedup <= 0:
        return 0.0
    raw = 100.0 * math.log(gm_speedup) / math.log(max(SPEEDUP_TARGET, 1.0000001))
    return max(0.0, min(100.0, raw))


def is_final_submission_role() -> bool:
    return os.environ.get("FRONTIER_SUBMISSION_ROLE", "agent") == "final"


# Hidden workloads. (Q, M, D, k). Agent role runs a fast subset for iterative
# feedback; the final verifier runs the full set. Seeds are derived from
# BASE_SEED so data is deterministic but not guessable from the statement.
_HIDDEN_WORKLOADS = (
    {"id": "w0", "Q": 2048, "M": 100_000,   "D": 64,  "k": 10},
    {"id": "w1", "Q": 4096, "M": 250_000,   "D": 128, "k": 10},
    {"id": "w2", "Q": 1024, "M": 1_000_000, "D": 96,  "k": 32},   # large-M regime
    {"id": "w3", "Q": 8192, "M": 200_000,   "D": 256, "k": 50},   # wide-D regime
    {"id": "w4", "Q": 2048, "M": 500_000,   "D": 64,  "k": 100},  # large-k regime
    {"id": "w5", "Q": 4096, "M": 300_000,   "D": 128, "k": 64},
)


def _workloads(*, final_role: bool) -> list[dict[str, Any]]:
    configured = _cfg("workloads", None)
    workloads = list(configured) if isinstance(configured, list) and configured else list(_HIDDEN_WORKLOADS)
    if not final_role:
        n_agent = _cfg_int("agent_workload_count", 3)
        workloads = workloads[:n_agent]
    for i, w in enumerate(workloads):
        w.setdefault("seed", BASE_SEED + 1000 * (i + 1))
    return workloads


# The worker runs the untrusted patched package in its own process. It imports
# the frozen baseline (refknn) and the patched knnlib, times both on identical
# seeded data, and reports per-workload timings + recall@k as JSON.
_WORKER_SOURCE = r'''
import argparse, json, sys, time, traceback
def _load(baseline_dir, patched_dir):
    sys.path.insert(0, patched_dir); sys.path.insert(0, baseline_dir)
    import refknn, knnlib
    return refknn, knnlib
def gen(Q, M, D, seed, device):
    import torch
    g = torch.Generator(device=device).manual_seed(int(seed))
    db = torch.randn(M, D, generator=g, device=device, dtype=torch.float32)
    queries = torch.randn(Q, D, generator=g, device=device, dtype=torch.float32)
    return queries, db
def recall(agent_idx, ref_idx):
    hit = (agent_idx.unsqueeze(2) == ref_idx.unsqueeze(1)).any(dim=2)
    Q, k = ref_idx.shape
    return float(hit.sum().item()) / (Q * k)
def bench(fn, warmup, iters):
    import torch
    for _ in range(warmup): fn(); torch.cuda.synchronize()
    ts = []
    for _ in range(iters):
        torch.cuda.synchronize(); t0 = time.perf_counter(); fn(); torch.cuda.synchronize()
        ts.append(time.perf_counter() - t0)
    ts.sort(); return ts[len(ts) // 2] * 1000.0
def check(out, Q, k):
    import torch
    if not (isinstance(out, tuple) and len(out) == 2): raise ValueError("knn must return (distances, indices)")
    dist, idx = out
    if tuple(dist.shape) != (Q, k) or tuple(idx.shape) != (Q, k): raise ValueError("wrong output shape")
    if not torch.isfinite(dist).all(): raise ValueError("non-finite distances")
def main():
    ap = argparse.ArgumentParser()
    for n in ("--baseline-dir","--patched-dir","--workloads","--out"): ap.add_argument(n, required=True)
    ap.add_argument("--warmup", type=int, default=3); ap.add_argument("--iters", type=int, default=7)
    a = ap.parse_args()
    import torch
    if not torch.cuda.is_available():
        json.dump({"ok": False, "error": "cuda_unavailable"}, open(a.out, "w")); return
    refknn, knnlib = _load(a.baseline_dir, a.patched_dir)
    rows = []
    for w in json.loads(a.workloads):
        Q, M, D, k, seed = w["Q"], w["M"], w["D"], w["k"], w["seed"]
        queries, db = gen(Q, M, D, seed, "cuda")
        ref_fn = lambda: refknn.knn(queries, db, k)
        agent_fn = lambda: knnlib.knn(queries, db, k)
        ref_out = ref_fn(); torch.cuda.synchronize()
        try:
            agent_out = agent_fn(); torch.cuda.synchronize(); check(agent_out, Q, k)
            rec = recall(agent_out[1].long(), ref_out[1].long())
        except Exception as e:
            rows.append({"id": w["id"], "ok": False, "error": type(e).__name__ + ": " + str(e)[:200]})
            del queries, db; torch.cuda.empty_cache(); continue
        ref_ms = bench(ref_fn, a.warmup, a.iters); agent_ms = bench(agent_fn, a.warmup, a.iters)
        rows.append({"id": w["id"], "ok": True, "ref_ms": ref_ms, "agent_ms": agent_ms, "recall": rec})
        del queries, db; torch.cuda.empty_cache()
    json.dump({"ok": True, "rows": rows}, open(a.out, "w"))
if __name__ == "__main__":
    try: main()
    except Exception: traceback.print_exc(); sys.exit(3)
'''


def _run_worker(patched_parent: Path, tmp_root: Path, env: dict[str, str],
                workloads: list[dict[str, Any]]) -> dict[str, Any]:
    worker_path = tmp_root / "knn_worker.py"
    worker_path.write_text(_WORKER_SOURCE, encoding="utf-8")
    out_path = tmp_root / "worker_out.json"
    cmd = [
        sys.executable, str(worker_path),
        "--baseline-dir", str(DEFAULT_BASELINE_SOURCE),
        "--patched-dir", str(patched_parent),
        "--workloads", json.dumps(workloads),
        "--out", str(out_path),
        "--warmup", str(WARMUP_ITERS),
        "--iters", str(TIMED_ITERS),
    ]
    run_checked(cmd, cwd=tmp_root, env=env, timeout=WORKER_TIMEOUT_SECONDS)
    return json.loads(out_path.read_text(encoding="utf-8"))


def full_evaluation(patch_path: Path, metrics: dict[str, Any]):
    final_role = is_final_submission_role()
    metrics["submission_role"] = "final" if final_role else "agent"
    workloads = _workloads(final_role=final_role)

    if not DEFAULT_CLEAN_SOURCE.exists() or not DEFAULT_BASELINE_SOURCE.exists():
        metrics["full_benchmark"] = 0
        return (1.0, 1.0,
                "patch policy smoke passed; knnlib judge source is not configured in this environment",
                metrics)

    with tempfile.TemporaryDirectory(prefix="knn_kernel_opt_") as tmp:
        tmp_root = Path(tmp)
        env = clean_env(tmp_root)
        patched_parent = tmp_root / "patched"
        shutil.copytree(DEFAULT_CLEAN_SOURCE, patched_parent)

        if int(metrics.get("changed_files", 0)) > 0:
            run_checked(["git", "apply", "--check", str(patch_path)], cwd=patched_parent, env=env, timeout=60)
            run_checked(["git", "apply", str(patch_path)], cwd=patched_parent, env=env, timeout=60)
            metrics["applied_patch"] = 1
        else:
            metrics["used_empty_patch"] = 1

        result = _run_worker(patched_parent, tmp_root, env, workloads)
        if not result.get("ok"):
            return _invalid(f"benchmark worker failed ({result.get('error', 'unknown')})", metrics)

        rows = result.get("rows", [])
        speedups: list[float] = []
        per_workload: dict[str, Any] = {}
        for row in rows:
            if not row.get("ok"):
                metrics["failed_workload_error"] = sanitize_error_text(str(row.get("error", "")))
                return _invalid("submitted knn crashed or returned an invalid result on a hidden workload", metrics)
            if row["recall"] < RECALL_THRESHOLD:
                metrics["recall_regression"] = {
                    "recall": row["recall"], "threshold": RECALL_THRESHOLD,
                }
                return _invalid("submitted knn recall regressed below threshold on a hidden workload", metrics)
            speedup = row["ref_ms"] / row["agent_ms"] if row["agent_ms"] > 0 else 0.01
            speedups.append(max(speedup, 0.01))
            per_workload[row["id"]] = {
                "ref_ms": row["ref_ms"], "agent_ms": row["agent_ms"], "speedup": speedup,
            }

        if not speedups:
            return _invalid("no workloads were evaluated", metrics)

        gm = geometric_mean(speedups)
        bounded = score_from_speedup(gm)
        metrics.update({
            "full_benchmark": 1,
            "workload_count": len(speedups),
            "geomean_speedup": gm,
        })
        if _cfg_bool("expose_per_workload_metrics", False):
            metrics["per_workload"] = per_workload
        return (bounded, bounded, f"knn geomean speedup {gm:.3f}x over the naive baseline", metrics)


def evaluate(solution_path: str) -> tuple[float, float, str, dict[str, Any]]:
    patch_path = Path(solution_path)
    ok, message, metrics = validate_patch(patch_path)
    if not ok:
        return _invalid(message, metrics)
    try:
        return full_evaluation(patch_path, metrics)
    except subprocess.TimeoutExpired:
        return _invalid("benchmark worker timed out", metrics)
    except subprocess.CalledProcessError as exc:
        stderr = sanitize_error_text(exc.stderr or "")
        cmd0 = Path(str(exc.cmd[0])).name if isinstance(exc.cmd, list) and exc.cmd else "subprocess"
        metrics["failed_command"] = "git apply" if cmd0 == "git" else cmd0
        metrics["stderr_tail"] = stderr
        return _invalid("patch apply or benchmark command failed", metrics)
    except Exception as exc:
        metrics["error_type"] = type(exc).__name__
        metrics["error_detail"] = sanitize_error_text(str(exc))
        return _invalid("evaluation failed", metrics)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: evaluator.py SOLUTION_PATCH", file=sys.stderr)
        return 2
    score, score_unbounded, message, metrics = evaluate(argv[1])
    print(json.dumps({
        "score": score,
        "score_unbounded": score_unbounded,
        "message": message,
        "metrics": metrics,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

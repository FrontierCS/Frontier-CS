"""nanowm_rollout_speedup evaluator (Frontier-CS 2.0 contract).

The agent submits a Python-only patch against a clean NanoWM checkout that
speeds up the diffusion SAMPLING for a fixed CSGO long-rollout invocation
(NanoWM-L/2, 50 frames, 4 context, nominal 50 DDIM steps). The judge applies the
patch, runs the rollout on a Modal GPU, and scores wall-clock speedup over the
unpatched baseline, gated by a rollout-quality (LPIPS-vs-GT) guardrail.

This file holds the self-contained static patch policy + scoring. Heavy
orchestration (Modal sandbox, baseline caching) lives in `speedup_eval/`. When
the GPU/Modal stack is unconfigured (local CI), the evaluator validates the
patch policy and returns a smoke score so the empty reference patch passes.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PKG = os.environ.get("FRONTIER_NWM_PKG", str(Path(__file__).resolve().parent))
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

from speedup_eval import scoring, settings as S  # noqa: E402

MAX_PATCH_BYTES = 256_000

# --- Patch policy ------------------------------------------------------------
# The agent may only change the diffusion SAMPLING layer (Python source). The
# model architecture, VAE, datasets, metric, and harness are frozen.
ALLOWED = (
    "src/diffusion/*.py",
    "src/diffusion/**/*.py",
    "src/sample/sampling_utils.py",
)
DENIED = (
    "src/models/**", "src/latent_codecs/**",          # frozen model + VAE
    "src/sample/evaluate_metrics.py", "src/sample/plot_metrics.py",  # the metric
    "src/sample/rollout.py",                           # the judge harness
    "src/wm_datasets/**",                              # data loading / no bench detection
    "src/experiments/**", "src/main.py", "src/utils/**",
    "**/*.so", "**/*.pyx", "**/*.c", "**/*.cpp", "**/*.cu",  # no native
    "**/setup.py", "**/pyproject.toml", "**/requirements*.txt",
)
# Forbidden substrings in ADDED lines (no benchmark detection / env leakage /
# timing short-circuits / hardcoded ground truth).
FORBIDDEN_TOKENS = (
    "FRONTIER_", "JUDGE_", "HARBOR_", "MODAL_", "HF_TOKEN", "NWM_TIME",
    "csgo_validation_start_indices", "val_starts", "val_files", "gen_seconds",
    "evaluate_metrics", "lpips", "ground_truth", "gt_frames",
    "os.environ", "subprocess", "socket", "/judge", "/opt/nanowm/baseline",
    "time.sleep", "while True",
)


@dataclass
class PatchFile:
    old_path: str = ""
    new_path: str = ""
    added_lines: list[str] = field(default_factory=list)

    @property
    def path(self) -> str:
        return self.new_path if self.new_path != "/dev/null" else self.old_path


def _match(path: str, patterns: tuple[str, ...]) -> bool:
    from fnmatch import fnmatch
    return any(fnmatch(path, pat) for pat in patterns)


def _parse_patch(text: str) -> list[PatchFile]:
    files: list[PatchFile] = []
    cur: PatchFile | None = None
    for line in text.splitlines():
        if line.startswith("diff --git"):
            if cur:
                files.append(cur)
            cur = PatchFile()
        elif line.startswith("--- "):
            if cur is None:
                cur = PatchFile()
            cur.old_path = line[4:].strip().removeprefix("a/")
        elif line.startswith("+++ "):
            if cur is None:
                cur = PatchFile()
            cur.new_path = line[4:].strip().removeprefix("b/")
        elif line.startswith("+") and not line.startswith("+++"):
            if cur is not None:
                cur.added_lines.append(line[1:])
    if cur:
        files.append(cur)
    return files


def _safe(path: str) -> bool:
    p = Path(path)
    return not p.is_absolute() and ".." not in p.parts


def validate_patch(patch_path: Path) -> tuple[bool, str, dict[str, Any]]:
    if not patch_path.exists():
        return False, "solution patch does not exist", {"valid_patch": 0}
    size = patch_path.stat().st_size
    if size > MAX_PATCH_BYTES:
        return False, f"patch too large ({size} > {MAX_PATCH_BYTES})", {"valid_patch": 0}
    text = patch_path.read_text(encoding="utf-8", errors="replace")
    metrics: dict[str, Any] = {
        "patch_bytes": size,
        "patch_sha256": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest(),
    }
    files = _parse_patch(text)
    metrics["files_changed"] = [f.path for f in files]
    if not files and size > 0:
        return False, "could not parse any file hunks from patch", {**metrics, "valid_patch": 0}
    for pf in files:
        for cand in {pf.old_path, pf.new_path, pf.path}:
            if cand and cand != "/dev/null" and not _safe(cand):
                return False, f"unsafe patch path: {cand}", {**metrics, "valid_patch": 0}
        if pf.new_path == "/dev/null":
            return False, f"deleting source files is out of scope: {pf.old_path}", {**metrics, "valid_patch": 0}
        path = pf.path
        if _match(path, DENIED) or not path.endswith((".py", ".pyi")):
            return False, f"path not allowed (frozen/native/harness): {path}", {**metrics, "valid_patch": 0}
        if not _match(path, ALLOWED):
            return False, f"path outside the allowlisted sampling layer: {path}", {**metrics, "valid_patch": 0}
        blob = "\n".join(pf.added_lines)
        for tok in FORBIDDEN_TOKENS:
            if tok in blob:
                return False, f"forbidden token in added lines ({tok}) in {path}", {**metrics, "valid_patch": 0}
    metrics["valid_patch"] = 1
    return True, "patch accepted by static policy", metrics


# --- Evaluate ----------------------------------------------------------------
def _resolve_patch(solution_path: str) -> Path:
    p = Path(solution_path)
    if p.is_dir():
        cand = p / "solution.patch"
        if cand.exists():
            return cand
        hits = sorted(p.rglob("*.patch"))
        if hits:
            return hits[0]
        return cand  # nonexistent -> validate_patch reports
    return p


def prepare() -> dict:
    return {"task": "nanowm_rollout_speedup", "smoke": S.SMOKE,
            "quality_tolerance": S.QUALITY_TOLERANCE, "nominal_steps": S.NUM_SAMPLING_STEPS}


def evaluate(solution_path: str):
    role = "final" if os.environ.get("FRONTIER_SUBMISSION_ROLE") == "final" else "agent"
    patch_path = _resolve_patch(solution_path)
    ok, msg, pmetrics = validate_patch(patch_path)
    if not ok:
        return 0.0, 0.0, f"patch rejected: {msg}", pmetrics

    # Local CI / no-GPU smoke: validate policy only, pass the (empty) reference.
    if S.SMOKE or not S.CKPT.exists():
        return 1.0, 1.0, "smoke: patch policy valid (GPU/Modal unconfigured)", {**pmetrics, "smoke": 1}

    # Heavy path: run baseline (cached) + patched rollout on the GPU sandbox.
    from speedup_eval import orchestrate  # Modal/GPU orchestration
    clips = S.FINAL_CLIPS if role == "final" else S.QUICK_CLIPS
    try:
        baseline, patched = orchestrate.run_pair(patch_path, clips=clips, role=role)
    except Exception as exc:  # concise public error only
        return 0.0, 0.0, f"evaluation failed: {type(exc).__name__}", {**pmetrics, "role": role}

    res = scoring.provisional_score(
        {"all": baseline["gen_seconds"]}, {"all": patched["gen_seconds"]},
        baseline["lpips"], patched["lpips"], tolerance=S.QUALITY_TOLERANCE,
    )
    metrics = {
        **pmetrics, "role": role, "clips": clips,
        "baseline_seconds": round(baseline["gen_seconds"], 2),
        "patched_seconds": round(patched["gen_seconds"], 2),
        "baseline_lpips": round(baseline["lpips"], 4),
        "patched_lpips": round(patched["lpips"], 4),
        "geomean_speedup": round(res["geomean_speedup"], 3),
        "quality_multiplier": round(res["quality_multiplier"], 3),
        "score_formula": "100*log2(speedup)*quality_mult; quality_mult<1 if LPIPS rises >tol over baseline",
    }
    msg = (f"speedup {res['geomean_speedup']:.2f}x "
           f"(lpips {patched['lpips']:.3f} vs baseline {baseline['lpips']:.3f}, "
           f"tol {S.QUALITY_TOLERANCE:.0%}); score {res['score']:.1f}")
    return res["score"], res["score_unbounded"], msg, metrics


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: evaluator.py <solution.patch|dir>")
        sys.exit(2)
    import json
    s, u, m, mt = evaluate(sys.argv[1])
    print(json.dumps({"score": s, "score_unbounded": u, "message": m, "metrics": mt}, indent=2))
    print(s)

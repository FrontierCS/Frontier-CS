"""Apply a sampler patch to a clean nano-world-model checkout, run the FIXED
CSGO rollout, and measure (generation wall-clock, LPIPS-vs-GT).

The judge fixes the rollout invocation (rollout_length / history / num_steps /
scheduling); the agent's patch may only change the *sampling internals*
(`src/diffusion/**`, `src/sample/sampling_utils.py`) to make that invocation
faster at iso-quality. Speedup = baseline_seconds / patched_seconds; quality =
LPIPS vs ground truth, guardrailed against the unpatched baseline.

Runnable standalone for local/Modal validation:
  python -m speedup_eval.runner --repo <clean> --patch <p.patch|->  \
      --out metrics.json [--steps 50 --clips 4]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import settings as S


def apply_patch(clean_repo: Path, patch_path: Path | None) -> Path:
    work = Path(tempfile.mkdtemp(prefix="nwm_speedup_"))
    repo = work / "repo"
    # symlink the heavy/immutable parts, copy only src/ so patches are cheap
    repo.mkdir(parents=True)
    for child in clean_repo.iterdir():
        if child.name == "src":
            shutil.copytree(child, repo / "src")
        else:
            (repo / child.name).symlink_to(child)
    if patch_path is not None and str(patch_path) != "-" and Path(patch_path).stat().st_size > 0:
        # The upstream checkout ships CRLF .py files, but a submitted/reference diff
        # is usually LF -- and the patch text is round-tripped through universal-
        # newline read_text() (orchestrate -> Modal) which strips CR. Mismatched
        # endings make git/patch reject with "patch does not apply (different line
        # endings)", so EVERY submission would score 0. Normalise BOTH the copied
        # target tree and the patch to LF so application is line-ending-agnostic
        # (LF .py executes identically; only the copy is touched, not the baseline).
        for py in (repo / "src").rglob("*.py"):
            b = py.read_bytes()
            if b"\r" in b:
                py.write_bytes(b.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        patch_lf = work / "patch.diff"
        patch_lf.write_bytes(Path(patch_path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        r = subprocess.run(["git", "apply", "--unsafe-paths", "--directory", str(repo),
                            str(patch_lf)], capture_output=True, text=True)
        if r.returncode != 0:
            # fall back to patch(1) (git apply needs a git root / clean context)
            r = subprocess.run(["patch", "-p1", "-d", str(repo), "-i", str(patch_lf)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                # patch(1) reports to stdout, git to stderr -- surface both.
                raise RuntimeError(f"patch failed: {(r.stdout + r.stderr)[:2000]}")
    # Inject the frozen-model guard into the (denied, judge-owned) rollout.py AFTER the
    # agent patch, so the model-frozen invariant is enforced at runtime even though the
    # static policy can't see a sampler-side runtime monkeypatch (the temp_embed gray area).
    inject_frozen_guard(repo)
    return repo


# The frozen-model guard, inlined into rollout.py at apply-time (self-contained: no
# import of speedup_eval from the rollout subprocess). Snapshot the params right after
# the model is loaded+eval'd; re-check after the rollout. A restored transient reshape
# (the causal-prefix temp_embed slice) passes; a persistently mutated model hard-errors
# -> nonzero exit -> scored as a submission execution failure (0). See
# speedup_eval/frozen_model_guard.py (unit-tested logic) and DESIGN.md s9.
_FG_SNAPSHOT = (
    "    # _FROZEN_GUARD (judge infra, injected by speedup_eval.runner; outside the\n"
    "    # agent's editable scope): the model is FROZEN -- a sampling patch may READ it\n"
    "    # but not PERSISTENTLY mutate it. Snapshot its params now; re-check after the\n"
    "    # rollout. A restored transient reshape (causal-prefix temp_embed) passes.\n"
    "    import hashlib as _hl_fg\n"
    "    def _fg_fp(_m):\n"
    "        _h = _hl_fg.sha256()\n"
    "        for _n, _p in sorted(_m.state_dict().items()):\n"
    "            _h.update(('%s|%s|%s' % (_n, tuple(_p.shape), _p.dtype)).encode())\n"
    "            _h.update(repr(float(_p.detach().to('cpu', dtype=torch.float64).sum())).encode())\n"
    "        return _h.hexdigest()\n"
    "    _fg_frozen = _fg_fp(model)\n"
)
_FG_VERIFY = (
    "    # _FROZEN_GUARD: enforce the frozen-model invariant after the rollout.\n"
    "    if _fg_fp(model) != _fg_frozen:\n"
    "        raise RuntimeError('frozen-model violation: the sampling patch persistently '\n"
    "                           'mutated the model parameters (the model is frozen; denied)')\n"
)


def inject_frozen_guard(repo: Path) -> None:
    """Insert the frozen-model guard into the copied src/sample/rollout.py. Anchors:
    snapshot just after `model.eval()`, verify just before the final `print("Done!...")`
    (after the rollout loop). FAIL CLOSED: if the anchors are not found (rollout.py
    structure changed) the guard cannot be placed, so RAISE rather than run unguarded."""
    f = repo / "src" / "sample" / "rollout.py"
    if not f.exists():
        return
    src = f.read_text()
    if "_fg_frozen" in src:  # idempotent
        return
    lines = src.splitlines(keepends=True)
    snap_at = verify_at = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if snap_at is None and s == "model.eval()":
            snap_at = i + 1
        if verify_at is None and (s.startswith('print(f"Done! Processed')
                                  or s.startswith("print(f'Done! Processed")
                                  or s.startswith('print("Done! Processed')):
            verify_at = i
    if snap_at is None or verify_at is None or verify_at <= snap_at:
        raise RuntimeError(
            "frozen-model guard injection failed: rollout.py anchors not found "
            f"(model.eval()@{snap_at}, Done@{verify_at}) -- refusing to run unguarded")
    lines.insert(verify_at, _FG_VERIFY)   # insert the later one first (indices stable)
    lines.insert(snap_at, _FG_SNAPSHOT)
    f.write_text("".join(lines))


def run_rollout(repo: Path, config: Path, ckpt: Path, save: Path, clips: int, steps: int,
                device: str = "cuda") -> float:
    """Run rollout.py; return generation wall-clock seconds (rollout-region timed
    inside; falls back to total wall)."""
    save.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CSGO_DATA_DIR"] = str(S.CSGO_DATA)
    env["NWM_TIME_FILE"] = str(save / "gen_seconds.txt")
    _apply_determinism_env(env)
    cmd = [sys.executable, "-u", "src/sample/rollout.py", "--config", str(config),
           "--ckpt", str(ckpt), "--save_path", str(save), "--num_samples", str(clips),
           "--batch_size", str(S.BATCH_SIZE), "--rollout_length", str(S.ROLLOUT_LENGTH),
           "--history_length", str(S.HISTORY_LENGTH), "--scheduling_mode", S.SCHEDULING_MODE,
           "--num_sampling_steps", str(steps), "--history_stabilization_level", str(S.HISTORY_STAB),
           "--fps", "8", "--seed", str(S.SEED)]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(repo), env=env, capture_output=True, text=True)
    wall = time.time() - t0
    if r.returncode != 0:
        raise RuntimeError(f"rollout failed (exit {r.returncode}): {r.stderr[-3000:]}")
    tf = save / "gen_seconds.txt"
    if tf.exists():
        try:
            return float(tf.read_text().strip())
        except Exception:
            pass
    return wall


def _apply_determinism_env(env: dict) -> None:
    """Determinism vars for the GPU subprocesses (rollout + the LPIPS metric).
    cuBLAS needs CUBLAS_WORKSPACE_CONFIG set before the first CUDA call, so it
    lives in the subprocess env, not toggled in-process. Pairs with the
    deterministic kernels enabled in rollout.py / evaluate_metrics.py so the
    baseline and patched arms share a bit-stable pipeline (common random numbers).
    NWM_DETERMINISM_STRICT=1 makes a missing deterministic kernel RAISE (proof
    mode) instead of silently running nondeterministically."""
    env.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    env.setdefault("PYTHONHASHSEED", "0")
    env["NWM_DETERMINISM_STRICT"] = "1" if S.STRICT_DETERMINISM else "0"


def lpips_vs_gt(repo: Path, save: Path) -> float:
    out_csv = save / "metrics.csv"
    env = {**os.environ, "CSGO_DATA_DIR": str(S.CSGO_DATA)}
    _apply_determinism_env(env)
    r = subprocess.run([sys.executable, "src/sample/evaluate_metrics.py", "--video_dir", str(save),
                        "--history_length", str(S.HISTORY_LENGTH), "--output_csv", str(out_csv)],
                       cwd=str(repo), env=env,
                       capture_output=True, text=True)
    if not out_csv.exists():
        raise RuntimeError(f"metrics failed: {r.stderr[-2000:]}")
    import pandas as pd
    return float(pd.read_csv(out_csv)["lpips"].mean())


def frames_lpips(dir_a: Path, dir_b: Path, device: str = "cuda") -> float | None:
    """Mean LPIPS between matching `sample_*_gen.mp4` in two rollout-output dirs --
    the FAITHFULNESS of the patched rollout to the baseline rollout (closeness of
    OUTPUTS, vs the quality metric's closeness to GROUND TRUTH). Returns None if
    nothing comparable is found. GPU; reuses the baked VGG weights."""
    import lpips
    import numpy as np
    import torch
    import imageio.v2 as imageio

    def _load(p: Path) -> "torch.Tensor":
        frames = [f for f in imageio.get_reader(str(p))]
        v = torch.from_numpy(np.stack(frames)).permute(0, 3, 1, 2).float() / 255.0
        return (v * 2.0 - 1.0).to(device)  # LPIPS expects [-1, 1]

    net = lpips.LPIPS(net="vgg").to(device).eval()
    vals: list[float] = []
    for ga in sorted(Path(dir_a).glob("*_gen.mp4")):
        gb = Path(dir_b) / ga.name
        if not gb.exists():
            continue
        a, b = _load(ga), _load(gb)
        t = min(a.shape[0], b.shape[0])
        with torch.no_grad():
            for i in range(t):
                vals.append(float(net(a[i:i + 1], b[i:i + 1]).mean().item()))
    return (sum(vals) / len(vals)) if vals else None


def evaluate(clean_repo: Path, patch_path: Path | None, config: Path, ckpt: Path,
             clips: int, steps: int, device: str = "cuda", keep_gen: Path | None = None) -> dict:
    repo = apply_patch(clean_repo, patch_path)
    try:
        save = repo / "_rollout_out"
        secs = run_rollout(repo, config, ckpt, save, clips, steps, device)
        lp = lpips_vs_gt(repo, save)
        if keep_gen is not None:  # stash generated frames for cross-arm faithfulness
            kp = Path(keep_gen); kp.mkdir(parents=True, exist_ok=True)
            for f in save.glob("*_gen.mp4"):
                shutil.copy(f, kp / f.name)
        return {"gen_seconds": secs, "lpips": lp, "clips": clips, "steps": steps}
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--patch", default="-")
    ap.add_argument("--config", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--clips", type=int, default=S.QUICK_CLIPS)
    ap.add_argument("--steps", type=int, default=S.NUM_SAMPLING_STEPS)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    m = evaluate(Path(a.repo), None if a.patch == "-" else Path(a.patch), Path(a.config),
                 Path(a.ckpt), a.clips, a.steps, a.device)
    Path(a.out).write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))

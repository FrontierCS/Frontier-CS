"""Apply a sampler patch to a clean nano-world-model checkout, run the FIXED
CSGO rollout, and measure (generation wall-clock, LPIPS-vs-GT).

The judge fixes the rollout invocation (rollout_length / history / num_steps /
scheduling); the agent's patch may only change the *sampling internals*
(`src/diffusion/**`, `src/sample/sampling_utils.py`) to make that invocation
reduce drift at iso-wall-clock. Speedup = baseline_seconds / patched_seconds; quality =
LPIPS vs ground truth, guardrailed against the unpatched baseline.

Runnable standalone for local/Modal validation:
  python -m stability_eval.runner --repo <clean> --patch <p.patch|->  \
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
        r = subprocess.run(["git", "apply", "--unsafe-paths", "--directory", str(repo),
                            str(patch_path)], capture_output=True, text=True)
        if r.returncode != 0:
            # fall back to patch(1) (git apply needs a git root / clean context)
            r = subprocess.run(["patch", "-p1", "-d", str(repo), "-i", str(patch_path)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"patch failed: {r.stderr[:2000]}")
    return repo


def run_rollout(repo: Path, config: Path, ckpt: Path, save: Path, clips: int, steps: int,
                device: str = "cuda") -> float:
    """Run rollout.py; return generation wall-clock seconds (rollout-region timed
    inside; falls back to total wall)."""
    save.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CSGO_DATA_DIR"] = str(S.CSGO_DATA)
    env["NWM_TIME_FILE"] = str(save / "gen_seconds.txt")
    cmd = [sys.executable, "-u", "src/sample/rollout.py", "--config", str(config),
           "--ckpt", str(ckpt), "--save_path", str(save), "--num_samples", str(clips),
           "--batch_size", str(S.BATCH_SIZE), "--rollout_length", str(S.ROLLOUT_LENGTH),
           "--history_length", str(S.HISTORY_LENGTH), "--scheduling_mode", S.SCHEDULING_MODE,
           "--num_sampling_steps", str(steps), "--history_stabilization_level", str(S.HISTORY_STAB),
           "--fps", "8"]
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


def lpips_vs_gt(repo: Path, save: Path) -> tuple[float, float]:
    """Returns (mean_lpips, tail_lpips) where tail = frames >= S.DRIFT_TAIL_START
    (the drifted region of a long rollout)."""
    out_csv = save / "metrics.csv"
    r = subprocess.run([sys.executable, "src/sample/evaluate_metrics.py", "--video_dir", str(save),
                        "--history_length", str(S.HISTORY_LENGTH), "--output_csv", str(out_csv)],
                       cwd=str(repo), env={**os.environ, "CSGO_DATA_DIR": str(S.CSGO_DATA)},
                       capture_output=True, text=True)
    if not out_csv.exists():
        raise RuntimeError(f"metrics failed: {r.stderr[-2000:]}")
    import pandas as pd
    df = pd.read_csv(out_csv)
    mean = float(df["lpips"].mean())
    tail_start = getattr(S, "DRIFT_TAIL_START", 60)
    g = df.groupby("frame_idx")["lpips"].mean()
    tail = float(g[g.index >= tail_start].mean()) if (g.index >= tail_start).any() else mean
    return mean, tail


def evaluate(clean_repo: Path, patch_path: Path | None, config: Path, ckpt: Path,
             clips: int, steps: int, device: str = "cuda") -> dict:
    repo = apply_patch(clean_repo, patch_path)
    try:
        save = repo / "_rollout_out"
        secs = run_rollout(repo, config, ckpt, save, clips, steps, device)
        lp, tail = lpips_vs_gt(repo, save)
        return {"gen_seconds": secs, "lpips": lp, "tail_lpips": tail, "clips": clips, "steps": steps}
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

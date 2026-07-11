"""Apply a sampler patch to a clean nano-world-model checkout, run the FIXED
CSGO rollout, and measure (generation wall-clock, LPIPS-vs-GT).

The judge fixes the rollout invocation (rollout_length / history / num_steps /
scheduling); the agent's patch may only change the *sampling internals*
(`src/diffusion/**`, `src/sample/sampling_utils.py`) to make that invocation
reduce drift at iso-wall-clock. Score = relative reduction in tail-frame LPIPS-vs-GT
over the unpatched baseline, gated by a wall-clock guardrail (patched gen time may
not exceed the baseline's by more than the tolerance).

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
    work = Path(tempfile.mkdtemp(prefix="nwm_stability_"))
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
    # agent patch, enforcing the model-frozen invariant at runtime (the static policy
    # cannot see a sampler-side runtime model monkeypatch). Matters more here than for
    # speedup: stability has NO patched-vs-baseline faithfulness backstop, so this is
    # the main guard against a persistent model mutation winning drift reduction.
    inject_frozen_guard(repo)
    return repo


# The frozen-model guard, inlined into rollout.py at apply-time (self-contained: no
# import of stability_eval from the rollout subprocess). Snapshot the params right
# after the model is loaded+eval'd; re-check after the rollout. A restored transient
# reshape (a causal-prefix-style temp_embed slice) passes; a persistently mutated model
# hard-errors -> nonzero exit -> scored as a submission execution failure (0).
_FG_SNAPSHOT = (
    "    # _FROZEN_GUARD (judge infra, injected by stability_eval.runner; outside the\n"
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
                device: str = "cuda", clip_offset: int = 0, rollout_length: int | None = None) -> float:
    """Run rollout.py; return generation wall-clock seconds (rollout-region timed
    inside; falls back to total wall). clip_offset processes only the GLOBAL clip
    window [clip_offset, clip_offset+clips) so a scored pair can fan out across
    Modal containers bit-identically (the per-batch seed keys on the global index).
    rollout_length defaults to the nominal S.ROLLOUT_LENGTH; the scored run passes a
    per-run RANDOM horizon (audit #7) so a hardcoded frame-position counter cannot
    target the tail. Both arms of a CRN pair receive the SAME value."""
    save.mkdir(parents=True, exist_ok=True)
    roll_len = int(rollout_length) if rollout_length is not None else S.ROLLOUT_LENGTH
    env = dict(os.environ)
    env["CSGO_DATA_DIR"] = str(S.CSGO_DATA)
    env["NWM_TIME_FILE"] = str(save / "gen_seconds.txt")
    _apply_determinism_env(env)
    cmd = [sys.executable, "-u", "src/sample/rollout.py", "--config", str(config),
           "--ckpt", str(ckpt), "--save_path", str(save), "--num_samples", str(clips),
           "--batch_size", str(S.BATCH_SIZE), "--rollout_length", str(roll_len),
           "--history_length", str(S.HISTORY_LENGTH), "--scheduling_mode", S.SCHEDULING_MODE,
           "--num_sampling_steps", str(steps), "--history_stabilization_level", str(S.HISTORY_STAB),
           "--fps", "8", "--seed", str(S.SEED), "--clip_offset", str(clip_offset)]
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


def lpips_vs_gt(repo: Path, save: Path, tail_start: int | None = None) -> tuple[float, float, int]:
    """Returns (mean_lpips, tail_lpips, n_clips) where tail = frames >= tail_start
    (the drifted region of a long rollout; defaults to the nominal S.DRIFT_TAIL_START,
    but the scored run passes the tail derived from its randomized horizon, audit #7).
    n_clips is the count of clips ACTUALLY produced (unique sample_id), so a fanned-out
    chunk is weighted by its REAL count -- the long-rollout headroom filter can drop an
    episode, leaving a chunk short, and weighting by the requested count would corrupt
    the grand mean."""
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
    try:
        df = pd.read_csv(out_csv)
    except Exception as e:  # column-less/empty CSV from an empty video dir
        raise RuntimeError(f"metrics produced an unreadable CSV ({e}); stderr: {r.stderr[-1000:]}")
    if df.empty or "lpips" not in df.columns or "sample_id" not in df.columns:
        raise RuntimeError(f"metrics CSV has no clips/rows (empty rollout?); stderr: {r.stderr[-1000:]}")
    n_clips = int(df["sample_id"].nunique())
    mean = float(df["lpips"].mean())
    ts = int(tail_start) if tail_start is not None else getattr(S, "DRIFT_TAIL_START", 60)
    g = df.groupby("frame_idx")["lpips"].mean()
    tail = float(g[g.index >= ts].mean()) if (g.index >= ts).any() else mean
    return mean, tail, n_clips


def evaluate(clean_repo: Path, patch_path: Path | None, config: Path, ckpt: Path,
             clips: int, steps: int, device: str = "cuda", clip_offset: int = 0,
             rollout_length: int | None = None) -> dict:
    repo = apply_patch(clean_repo, patch_path)
    roll_len = int(rollout_length) if rollout_length is not None else S.ROLLOUT_LENGTH
    tail_start = S.tail_start_for(roll_len)
    try:
        save = repo / "_rollout_out"
        secs = run_rollout(repo, config, ckpt, save, clips, steps, device,
                           clip_offset=clip_offset, rollout_length=roll_len)
        # An empty clip window (clip_offset at/over the valid-slice count) produces
        # no videos; report 0 clips so the fan-out aggregator skips it cleanly
        # instead of crashing the metric subprocess on a column-less CSV.
        if not list(save.glob("*_gen.mp4")):
            return {"gen_seconds": secs, "lpips": None, "tail_lpips": None, "clips": 0,
                    "steps": steps, "rollout_length": roll_len, "tail_start": tail_start}
        lp, tail, n_clips = lpips_vs_gt(repo, save, tail_start=tail_start)
        # 'clips' is the ACTUAL processed count (not the requested arg), so a chunk
        # short of its request is weighted/divided correctly downstream.
        return {"gen_seconds": secs, "lpips": lp, "tail_lpips": tail, "clips": n_clips,
                "steps": steps, "rollout_length": roll_len, "tail_start": tail_start}
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

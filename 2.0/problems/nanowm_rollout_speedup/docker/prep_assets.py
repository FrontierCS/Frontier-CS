#!/usr/bin/env python3
"""Auto-prepare the (public) NanoWM rollout-task assets so the build is
self-contained -- no hand-staged NWM_ASSETS required. Invoked by build_images.sh
when the staging dir is empty; safe to run standalone.

Produces, under --out (the NWM_ASSETS layout build_images.sh consumes):
  ckpts/nanowm-l2-csgo-100k/model_state_dict.pt   (converted from HF safetensors)
  ckpts/nanowm-l2-csgo-100k/config.yaml
  csgo/1-200/hdf5_dm_july2021_<N>.hdf5             (ONLY the held-out val episodes)
  csgo_subset/{val_files.txt,val_starts.npy}       (derived from the repo split)

Public sources (verified public, no token / no gating / no terms):
  checkpoint : HF model   knightnemo/nanowm-l2-csgo-100k       (model.safetensors, 2.23 GB)
  csgo data  : HF dataset TeaPearce/CounterStrike_Deathmatch   (hdf5_dm_july2021_1_to_200.tar, 25.7 GB)
  val subset : DERIVED from nano-world-model/src/.../csgo_splits/{test_split.txt,
               csgo_validation_start_indices.npy} -- the held-out subset is exactly
               the test_split episodes with number <= 200 (22 clips), which is the
               1-200 data chunk the task stages. No download, no seed needed.

Notes:
  * The HF model ships `model.safetensors`, not the `model_state_dict.pt` the
    upstream loader (`utils.nanowm_utils.find_model` -> torch.load) expects, so we
    convert. find_model strips a leading `model.`/`_orig_mod.` prefix and unwraps a
    `model` key, so a bare state_dict loads cleanly.
  * The dataset is stored as 200-episode TAR chunks (no individual .hdf5), so we
    download the single 1-200 chunk to a temp dir, extract ONLY the ~22 needed
    members, then delete the tar -- the staged data is ~3 GB, not 25.7 GB.
  * Idempotent: each step is skipped if its output already exists.
  * Keep this judge/operator-side ONLY; the agent image never sees these assets.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

CKPT_REPO = "knightnemo/nanowm-l2-csgo-100k"
DATA_REPO = "TeaPearce/CounterStrike_Deathmatch"
DATA_TAR = "hdf5_dm_july2021_1_to_200.tar"
NANOWM_REPO_URL = "https://github.com/simchowitzlabpublic/nano-world-model"
MAX_EPISODE = 200  # held-out subset = test_split episodes with number <= this


def _ep_num(fn: str) -> int:
    m = re.search(r"_(\d+)\.hdf5$", fn)
    return int(m.group(1)) if m else 10**9


def _splits_dir(repo_hint: str) -> Path:
    """Locate (or clone) the csgo_splits dir holding the public split files."""
    rel = "src/wm_datasets/data_source/game/csgo_splits"
    if repo_hint:
        cand = Path(repo_hint) / rel
        if (cand / "test_split.txt").exists():
            return cand
        cand = Path(repo_hint)  # maybe repo_hint already points at the splits dir
        if (cand / "test_split.txt").exists():
            return cand
    tmp = Path(tempfile.mkdtemp(prefix="nwm_splits_")) / "repo"
    print(f"[splits] cloning {NANOWM_REPO_URL} (shallow) for split files ...", flush=True)
    subprocess.run(["git", "clone", "--depth", "1", NANOWM_REPO_URL, str(tmp)], check=True)
    return tmp / rel


def derive_val_subset(splits: Path, out_dir: Path) -> list[str]:
    import numpy as np
    test = [l.strip() for l in (splits / "test_split.txt").read_text().splitlines() if l.strip()]
    starts = np.load(splits / "csgo_validation_start_indices.npy")
    if len(starts) != len(test):
        raise SystemExit(f"split/start length mismatch: {len(starts)} starts vs {len(test)} files")
    sel = [(i, f) for i, f in enumerate(test) if _ep_num(f) <= MAX_EPISODE]
    files = [f for _, f in sel]
    sub_starts = np.array([int(starts[i]) for i, _ in sel], dtype=np.int64)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "val_files.txt").write_text("\n".join(files) + "\n")
    np.save(out_dir / "val_starts.npy", sub_starts)
    print(f"[val] derived {len(files)} held-out clips -> {out_dir}", flush=True)
    return files


def ensure_ckpt(out: Path) -> None:
    dst = out / "ckpts" / "nanowm-l2-csgo-100k"
    pt = dst / "model_state_dict.pt"
    if pt.exists():
        print(f"[ckpt] exists, skip ({pt})", flush=True)
        return
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    import torch
    dst.mkdir(parents=True, exist_ok=True)
    print(f"[ckpt] downloading {CKPT_REPO} model.safetensors (~2.23 GB) ...", flush=True)
    st = hf_hub_download(CKPT_REPO, "model.safetensors")
    cfg = hf_hub_download(CKPT_REPO, "config.yaml")
    shutil.copy(cfg, dst / "config.yaml")
    torch.save(load_file(st), pt)  # torch-loadable .pt for upstream find_model()
    print(f"[ckpt] wrote {pt} ({pt.stat().st_size / 1e9:.2f} GB)", flush=True)


def ensure_data(out: Path, files: list[str]) -> None:
    dst = out / "csgo" / "1-200"
    needed = set(files)
    have = {p.name for p in dst.glob("*.hdf5")} if dst.exists() else set()
    missing = needed - have
    if not missing:
        print(f"[data] all {len(needed)} episodes present, skip", flush=True)
        return
    from huggingface_hub import hf_hub_download
    dst.mkdir(parents=True, exist_ok=True)
    # Download into the HF cache (resumable across runs); a 25.7 GB pull is too
    # fragile to restart from scratch on an interruption. The cached tar is left
    # in ~/.cache/huggingface afterwards (purge with `huggingface-cli delete-cache`
    # to reclaim ~25.7 GB once the 22 episodes are staged).
    print(f"[data] downloading {DATA_TAR} (~25.7 GB, resumable HF cache) ...", flush=True)
    tarp = hf_hub_download(DATA_REPO, DATA_TAR, repo_type="dataset")
    with tarfile.open(tarp) as tf:
        members = {Path(m.name).name: m for m in tf.getmembers() if m.name.endswith(".hdf5")}
        for fn in sorted(missing):
            m = members.get(fn)
            if m is None:
                raise SystemExit(f"{fn} not found in {DATA_TAR}; sample members={list(members)[:3]}")
            m.name = fn  # flatten into 1-200/<name>.hdf5
            tf.extract(m, dst)
            print(f"[data] extracted {fn}", flush=True)
    print(f"[data] staged {len(needed)} episodes -> {dst}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-stage public NanoWM rollout assets.")
    ap.add_argument("--out", required=True, help="NWM_ASSETS staging dir to populate")
    ap.add_argument("--repo", default="", help="optional nano-world-model checkout (for split files)")
    ap.add_argument("--skip-data", action="store_true", help="stage ckpt+val only (skip the 25.7 GB data)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = derive_val_subset(_splits_dir(a.repo), out / "csgo_subset")
    ensure_ckpt(out)
    if not a.skip_data:
        ensure_data(out, files)
    print(f"[done] assets staged under {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

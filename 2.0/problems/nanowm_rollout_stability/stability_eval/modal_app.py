"""Modal app: run NanoWM CSGO rollouts (patched and/or vanilla) on one GPU.

Mirrors the GPU-on-Modal pattern of vllm_llm_serving_optimization: the judge
container stays CPU-only and calls into a Modal GPU function. The NanoWM
checkout, L/2 CSGO checkpoint, and held-out CSGO episode subset are baked into
the Modal image at build time; the agent's patch text travels in per call.

Parametrized via env vars (set by the judge):
    NWM_MODAL_GPU      Modal GPU string (default "H100")
    NWM_MODAL_APP      Modal app name
    NWM_HF_SECRET      Modal Secret name (unused once weights are baked)

Deploy:  modal deploy stability_eval/modal_app.py
Call:
    run_pair_remote(patch_text, clips, steps)  -> {"baseline":{...}, "patched":{...}}
        Runs BOTH arms back-to-back in one container on one GPU (two rollout
        subprocesses) so the scored (final) result shares hardware/driver/seed.
        The no-op->0 CRN guarantee additionally relies on the determinism flags
        holding for every op (audit P1; prove once on H100 with strict mode).
    run_rollout_remote(patch_text, clips, steps) -> metrics dict
        Single arm; used for cheap cached-baseline iterative (agent-role) feedback.

NOTE: validated structurally against the #145 modal pattern; end-to-end Modal
execution is pending maintainer Modal credentials (Della has no Modal access).
The LOCAL backend (orchestrate._run_local / _run_pair_local) is the path
validated on H100 -- the same SKU now requested here, so the production path and
the calibrated numbers share one GPU type.
"""
from __future__ import annotations

import os

GPU = os.environ.get("NWM_MODAL_GPU", "H100")
APP_NAME = os.environ.get("NWM_MODAL_APP", "nanowm-rollout-stability")
REMOTE_ROOT = "/opt/nanowm"

# cuBLAS determinism must be set before the first CUDA call; bake it into the
# image env so the rollout subprocess inherits it (pairs with the deterministic
# kernels enabled in rollout.py via the infra patch).
_DETERMINISM_ENV = {"CUBLAS_WORKSPACE_CONFIG": ":4096:8", "PYTHONHASHSEED": "0"}

try:
    import modal

    image = (
        modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.11")
        # runner.apply_patch shells out to `git apply` (fallback `patch -p1`); the
        # CUDA base ships neither, so the patched arm died with FileNotFoundError
        # ('git') before any rollout — the baseline arm (no patch) never hit it.
        .apt_install("git", "patch")
        .pip_install(
            "torch==2.4.1", "torchvision==0.19.1", "numpy<2", "scipy==1.15.3",
            "lpips", "diffusers[torch]==0.24.0", "omegaconf", "hydra-core",
            "decord", "imageio", "imageio-ffmpeg", "opencv-python-headless",
            "scikit-image", "pandas", "einops", "timm", "pytorch-lightning==2.4.0",
            "huggingface_hub==0.25.2", "transformers==4.46.3",
            # rollout import-chain deps the hand-curated list omitted (the Modal
            # path had never run a rollout end-to-end before): h5py reads the CSGO
            # .hdf5 episodes (wm_datasets), tensorboard backs the SummaryWriter
            # import at the top of utils/nanowm_utils.py pulled in by find_model.
            "h5py", "tensorboard",
            # metric-path deps (utils.metrics, imported by evaluate_metrics.py):
            # piqa backs PSNR/SSIM, pytorch-fid the InceptionV3 the Evaluator ctor
            # builds, requests is a top-level import in utils.fvd. FVD/I3D is never
            # computed (only LPIPS is scored) but these module/ctor imports must
            # resolve or the metric subprocess dies before writing any LPIPS.
            "piqa", "pytorch-fid", "requests",
        )
        # Pre-fetch the metric model weights at BUILD time so scoring never depends
        # on a flaky per-container runtime download: LPIPS' VGG16 backbone and the
        # InceptionV3 the Evaluator ctor builds were fetched from download.pytorch.org
        # on every cold container and intermittently hit "Connection reset by peer",
        # which would zero out a whole scored run. Baked into the torch hub cache,
        # the runtime Evaluator finds them locally.
        .run_commands(
            "python -c 'import lpips; lpips.LPIPS(net=\"vgg\"); "
            "from pytorch_fid.inception import InceptionV3; "
            "InceptionV3([InceptionV3.BLOCK_INDEX_BY_DIM[2048]])'"
        )
        .env(_DETERMINISM_ENV)
        # bake the clean checkout + ckpt + CSGO subset + task package
        .add_local_dir(os.environ.get("NWM_BAKE_DIR", "/opt/nanowm"), REMOTE_ROOT, copy=True)
    )
    app = modal.App(APP_NAME)

    def _eval_arm(patch_text: str, clips: int, steps: int, strict: bool = False,
                  clip_offset: int = 0, rollout_length: int | None = None) -> dict:
        import sys, tempfile
        from pathlib import Path
        # Propagate the judge's strict-determinism choice INTO this Modal container
        # BEFORE settings is imported: the flag is set on the CPU judge, not here,
        # so without this S.STRICT_DETERMINISM (hence the rollout/metric subprocess
        # NWM_DETERMINISM_STRICT) would always read 0 (warn_only) on the GPU and the
        # H100 proof run would prove nothing about op-level determinism.
        os.environ["FRONTIER_NWM_STRICT_DETERMINISM"] = "1" if strict else "0"
        sys.path.insert(0, f"{REMOTE_ROOT}/task")
        from stability_eval import runner, orchestrate, settings as S  # noqa
        patch = None
        if patch_text.strip():
            p = Path(tempfile.mkstemp(suffix=".patch")[1])
            p.write_text(patch_text)
            patch = p
        cfg = orchestrate._compose_config()
        # rollout_length is decided ONCE on the judge (audit #7 randomized horizon)
        # and passed in identically for every chunk + both arms, so chunk
        # bit-identity and CRN pairing are unaffected.
        return runner.evaluate(S.REPO, patch, cfg, S.CKPT, clips=clips, steps=steps,
                               device="cuda", clip_offset=clip_offset,
                               rollout_length=rollout_length)

    # Strict determinism (TF32 off + deterministic kernels) ~triples the sampling
    # wall-clock and the 80-frame stability rollout is slow, so the scored 22-clip
    # pair would be ~10h sequentially. Instead run_pair_remote FANS it out across
    # containers, one batch_size-aligned clip CHUNK each -- the per-batch seed keys
    # on the GLOBAL clip index, so chunks are bit-identical to one sequential run.
    @app.function(gpu=GPU, image=image, timeout=14400)  # 4h: single-arm quick run
    def _rollout(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:
        return _eval_arm(patch_text, clips, steps, strict)

    @app.function(gpu=GPU, image=image, timeout=21600)  # 6h: one chunk's baseline+patched pair
    def _rollout_pair_chunk(spec) -> dict:
        # spec = (clip_offset, clip_count, patch_text, steps, strict, rollout_length).
        # Runs BOTH arms for the GLOBAL clip window [clip_offset, clip_offset+clip_count)
        # on ONE container, so the pair shares hardware AND the global per-clip seed
        # (CRN). rollout_length is the per-run randomized horizon (audit #7), identical
        # across all chunks (decided on the judge), so the fan-out stays bit-identical.
        clip_offset, clip_count, patch_text, steps, strict, rollout_length = spec
        baseline = _eval_arm("", clip_count, steps, strict, clip_offset, rollout_length)
        patched = _eval_arm(patch_text, clip_count, steps, strict, clip_offset, rollout_length)
        # Use the ACTUAL processed count (the 80-frame headroom filter can drop an
        # episode): both arms see the SAME clips, so they must agree -- and the real
        # count, not the requested one, drives the downstream weighting/divisor.
        nb, npp = int(baseline.get("clips", 0)), int(patched.get("clips", 0))
        if nb != npp:
            raise RuntimeError(f"chunk@{clip_offset}: baseline/patched clip-count mismatch {nb} != {npp}")
        return {"clip_offset": clip_offset, "requested": clip_count, "clip_count": nb,
                "baseline": baseline, "patched": patched}

    def run_rollout_remote(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:
        with app.run():
            return _rollout.remote(patch_text, clips, steps, strict)

    def run_pair_remote(patch_text: str, clips: int, steps: int, strict: bool = False,
                        chunk_size: int = 4, rollout_length: int | None = None) -> dict:
        # Fan the scored pair out across Modal containers, one batch_size-aligned
        # clip chunk each (chunk_size must be a multiple of the rollout batch_size,
        # enforced by the caller, so chunk offsets land on global batch boundaries
        # and reproduce the sequential run's batches bit-for-bit). Aggregate:
        # tail/lpips are per-clip-weighted means; gen_seconds is the SUM (total
        # sampling compute, for the wall-clock guardrail -- each chunk's two arms
        # ran on the same container so their ratio is a fair paired comparison).
        # rollout_length (audit #7) is the SAME value in every spec so the fan-out is
        # bit-identical to one sequential run at that horizon.
        specs, off = [], 0
        while off < clips:
            cnt = min(chunk_size, clips - off)
            specs.append((off, cnt, patch_text, steps, strict, rollout_length))
            off += cnt
        # Modal .map raises (return_exceptions=False) if any chunk's rollout/metric
        # errors -> the whole scored run hard-fails (correct: never score a partial
        # result on a real error). Empty-window chunks instead return clip_count=0
        # and are dropped here; a clip SHORTFALL (the headroom filter dropping an
        # episode) is scored on the actual set, weighted correctly, but logged.
        with app.run():
            results = [r for r in _rollout_pair_chunk.map(specs) if r and r.get("clip_count", 0) > 0]
        tot = sum(r["clip_count"] for r in results)
        if tot == 0:
            raise RuntimeError("no clips processed across any chunk (empty valid-slice set?)")
        if tot != clips:
            print(f"[run_pair_remote] WARNING: requested {clips} clips but processed {tot} "
                  f"(some episodes lack long-rollout headroom); scoring on {tot}, "
                  f"weighted correctly -- NOT silently mis-divided.")

        # The randomized scored horizon (audit #7) is identical across chunks/arms;
        # surface it (and the derived tail) so the evaluator/operator can see/repro it.
        _roll = next((r["baseline"].get("rollout_length") for r in results), rollout_length)
        _tail = next((r["baseline"].get("tail_start") for r in results), None)

        def _agg(arm: str) -> dict:
            # Per-clip-weighted grand mean: sum(chunk_mean * chunk_clips) / total
            # equals the sequential mean-over-all-clips (the chunk-size factor
            # cancels) up to FP summation order. gen_seconds is the SUM (total
            # sampling compute) -- a fair paired ratio vs baseline, not a
            # bit-reproducible sequential time.
            return {
                "tail_lpips": sum(r[arm]["tail_lpips"] * r["clip_count"] for r in results) / tot,
                "lpips": sum(r[arm]["lpips"] * r["clip_count"] for r in results) / tot,
                "gen_seconds": sum(r[arm]["gen_seconds"] for r in results),
                "clips": tot, "steps": steps, "rollout_length": _roll, "tail_start": _tail,
            }
        # Wall-clock over-budget for the guardrail: the clip-weighted mean of each
        # chunk's OWN patched/baseline ratio (both arms ran on ONE board, so each
        # ratio is a fair paired comparison), NOT the ratio of cross-board summed
        # times. Carried on the patched dict so the (baseline, patched) return arity
        # is unchanged and the evaluator can prefer it over the summed-time ratio.
        def _chunk_rel(r):
            b = max(r["baseline"]["gen_seconds"], 1e-9)
            return max(0.0, (r["patched"]["gen_seconds"] - b) / b)
        wallclock_rel_over = sum(_chunk_rel(r) * r["clip_count"] for r in results) / tot
        baseline, patched = _agg("baseline"), _agg("patched")
        patched["wallclock_rel_over"] = wallclock_rel_over
        return {"baseline": baseline, "patched": patched,
                "chunks": len(results), "requested_clips": clips, "scored_clips": tot,
                "wallclock_rel_over": wallclock_rel_over,
                "rollout_length": _roll, "tail_start": _tail}

except ImportError:  # modal not installed (e.g. local validation)
    def run_rollout_remote(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:  # type: ignore
        raise RuntimeError("modal not available; use the LOCAL backend (FRONTIER_NWM_BACKEND=local)")

    def run_pair_remote(patch_text: str, clips: int, steps: int, strict: bool = False,
                        chunk_size: int = 4, rollout_length: int | None = None) -> dict:  # type: ignore
        raise RuntimeError("modal not available; use the LOCAL backend (FRONTIER_NWM_BACKEND=local)")

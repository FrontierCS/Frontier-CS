"""Modal app: run NanoWM CSGO rollouts (patched and/or vanilla) on one GPU.

Mirrors the GPU-on-Modal pattern of vllm_llm_serving_optimization: the judge
container stays CPU-only and calls into a Modal GPU function. The NanoWM
checkout, L/2 CSGO checkpoint, and held-out CSGO episode subset are baked into
the Modal image at build time; the agent's patch text travels in per call.

Parametrized via env vars (set by the judge):
    NWM_MODAL_GPU      Modal GPU string (default "H100")
    NWM_MODAL_APP      Modal app name
    NWM_HF_SECRET      Modal Secret name (unused once weights are baked)

Deploy:  modal deploy speedup_eval/modal_app.py
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
APP_NAME = os.environ.get("NWM_MODAL_APP", "nanowm-rollout-speedup")
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
        # which would zero out a whole 22-clip scored run. Baked into the torch hub
        # cache, the runtime Evaluator finds them locally.
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
                  keep_gen=None) -> dict:
        import sys, tempfile
        from pathlib import Path
        # Propagate the judge's strict-determinism choice INTO this Modal container
        # BEFORE settings is imported: the flag is set on the CPU judge, not here,
        # so without this S.STRICT_DETERMINISM (hence the rollout/metric subprocess
        # NWM_DETERMINISM_STRICT) would always read 0 (warn_only) on the GPU and the
        # H100 proof run would prove nothing about op-level determinism.
        os.environ["FRONTIER_NWM_STRICT_DETERMINISM"] = "1" if strict else "0"
        sys.path.insert(0, f"{REMOTE_ROOT}/task")
        from speedup_eval import runner, orchestrate, settings as S  # noqa
        patch = None
        if patch_text.strip():
            p = Path(tempfile.mkstemp(suffix=".patch")[1])
            p.write_text(patch_text)
            patch = p
        cfg = orchestrate._compose_config()
        return runner.evaluate(S.REPO, patch, cfg, S.CKPT, clips=clips, steps=steps,
                               device="cuda", keep_gen=keep_gen)

    # Timeouts are generous: strict determinism (TF32 off + deterministic kernels)
    # roughly triples the sampling wall-clock, and the long 80-frame stability
    # rollout runs ~1560s per 2-clip batch on H100 -> a 22-clip baseline+patched
    # pair is ~9-10h. Single-arm (quick/agent-role) tops out near ~2h.
    @app.function(gpu=GPU, image=image, timeout=14400)  # 4h: single-arm quick run
    def _rollout(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:
        return _eval_arm(patch_text, clips, steps, strict)

    @app.function(gpu=GPU, image=image, timeout=43200)  # 12h: scored baseline+patched pair
    def _rollout_pair(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:
        # Baseline and patched on the SAME container/GPU (each its own rollout
        # subprocess): identical hardware, driver, image and (with the infra-patch
        # seeding) identical initial noise. This removes cross-container/-hardware
        # variance; bit-equality for a no-op still depends on the determinism
        # flags holding for every op (prove once on H100 with strict mode).
        import sys, tempfile
        from pathlib import Path
        base_dir = tempfile.mkdtemp(prefix="nwm_faith_base_")
        patch_dir = tempfile.mkdtemp(prefix="nwm_faith_patch_")
        baseline = _eval_arm("", clips, steps, strict, keep_gen=base_dir)
        patched = _eval_arm(patch_text, clips, steps, strict, keep_gen=patch_dir)
        # (A) Faithfulness: how far the patched rollout's frames drifted from the
        # baseline rollout's frames (closeness of OUTPUTS, not just to GT). Carried
        # on the patched dict so run_pair's (baseline, patched) arity is unchanged.
        try:
            sys.path.insert(0, f"{REMOTE_ROOT}/task")
            from speedup_eval import runner as _r
            patched["faithfulness_lpips"] = _r.frames_lpips(Path(base_dir), Path(patch_dir), "cuda")
        except Exception as _e:
            patched["faithfulness_lpips"] = None
        return {"baseline": baseline, "patched": patched}

    def run_rollout_remote(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:
        with app.run():
            return _rollout.remote(patch_text, clips, steps, strict)

    def run_pair_remote(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:
        with app.run():
            return _rollout_pair.remote(patch_text, clips, steps, strict)

except ImportError:  # modal not installed (e.g. local validation)
    def run_rollout_remote(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:  # type: ignore
        raise RuntimeError("modal not available; use the LOCAL backend (FRONTIER_NWM_BACKEND=local)")

    def run_pair_remote(patch_text: str, clips: int, steps: int, strict: bool = False) -> dict:  # type: ignore
        raise RuntimeError("modal not available; use the LOCAL backend (FRONTIER_NWM_BACKEND=local)")

"""Modal app: run one NanoWM CSGO rollout (patched or vanilla) on one GPU.

Mirrors the GPU-on-Modal pattern of vllm_llm_serving_optimization: the judge
container stays CPU-only and calls into a Modal GPU function. The NanoWM
checkout, L/2 CSGO checkpoint, and held-out CSGO episode subset are baked into
the Modal image at build time; the agent's patch text travels in per call.

Parametrized via env vars (set by the judge):
    NWM_MODAL_GPU      Modal GPU string (default "L40S")
    NWM_MODAL_APP      Modal app name
    NWM_HF_SECRET      Modal Secret name (unused once weights are baked)

Deploy:  modal deploy speedup_eval/modal_app.py
Call:    run_rollout_remote(patch_text, clips, steps) -> metrics dict

NOTE: validated structurally against the #145 modal pattern; end-to-end Modal
execution is pending maintainer Modal credentials (Della has no Modal access).
The LOCAL backend (orchestrate._run_local) is the path validated on H100.
"""
from __future__ import annotations

import os

GPU = os.environ.get("NWM_MODAL_GPU", "L40S")
APP_NAME = os.environ.get("NWM_MODAL_APP", "nanowm-rollout-speedup")
REMOTE_ROOT = "/opt/nanowm"

try:
    import modal

    image = (
        modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.11")
        .pip_install(
            "torch==2.4.1", "torchvision==0.19.1", "numpy<2", "scipy==1.15.3",
            "lpips", "diffusers[torch]==0.24.0", "omegaconf", "hydra-core",
            "decord", "imageio", "imageio-ffmpeg", "opencv-python-headless",
            "scikit-image", "pandas", "einops", "timm", "pytorch-lightning==2.4.0",
            "huggingface_hub==0.25.2", "transformers==4.46.3",
        )
        # bake the clean checkout + ckpt + CSGO subset + task package
        .add_local_dir(os.environ.get("NWM_BAKE_DIR", "/opt/nanowm"), REMOTE_ROOT, copy=True)
    )
    app = modal.App(APP_NAME)

    @app.function(gpu=GPU, image=image, timeout=3600)
    def _rollout(patch_text: str, clips: int, steps: int) -> dict:
        import sys, tempfile
        from pathlib import Path
        sys.path.insert(0, f"{REMOTE_ROOT}/task")
        from speedup_eval import runner, orchestrate  # noqa
        patch = None
        if patch_text.strip():
            p = Path(tempfile.mkstemp(suffix=".patch")[1])
            p.write_text(patch_text)
            patch = p
        cfg = orchestrate._compose_config()
        from speedup_eval import settings as S
        return runner.evaluate(S.REPO, patch, cfg, S.CKPT, clips=clips, steps=steps, device="cuda")

    def run_rollout_remote(patch_text: str, clips: int, steps: int) -> dict:
        with app.run():
            return _rollout.remote(patch_text, clips, steps)

except ImportError:  # modal not installed (e.g. local validation)
    def run_rollout_remote(patch_text: str, clips: int, steps: int) -> dict:  # type: ignore
        raise RuntimeError("modal not available; use the LOCAL backend (FRONTIER_NWM_BACKEND=local)")

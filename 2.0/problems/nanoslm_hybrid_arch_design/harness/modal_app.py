"""Modal app: run the nanoslm_hybrid_arch_design judge on one GPU.

Mirrors the GPU-on-Modal pattern of vllm_llm_serving_optimization and nanowm:
the judge container stays CPU-only and calls into a Modal GPU function.

Two things make this app much lighter than lm_arch_discovery's:

  * NO EXTERNAL REPO AND NO CUDA SOURCE BUILD. The harness is self-contained
    PyTorch; the only third-party imports across harness/*.py are torch and
    numpy. torch's own wheels ship the CUDA runtime, so a slim base works and
    the image builds in ~1 min rather than needing nvcc.
  * NO DATASET DOWNLOAD AND NO GATED TOKENIZER. The corpus is PRE-TOKENIZED by
    docker/prep_assets.py with dolma2 (allenai/dolma2-tokenizer, vocab 100278 --
    ungated, no HF token), so this image never tokenizes anything; and
    harness/data.py falls back to a deterministic synthetic TOKEN stream when
    the .bin paths are absent. So the wiring is provable before any corpus is
    staged; a real shard is mounted later for calibration.

    CAVEAT while no shard is mounted here: with the synthetic stream there is no
    underlying text, so the bits-per-byte denominator comes from
    settings.SYNTHETIC_BYTES_PER_TOKEN (the measured dolma2 compression ratio)
    rather than from a manifest. Smoke bpb is therefore in the right RANGE but
    is not a measurement of anything. Staging the real train.bin/val.bin/
    manifest.json on this image is required before calibration.

Rather than reimplement the training loop here, this calls evaluator.evaluate()
-- the SAME entrypoint Harbor calls -- so there is no second code path to drift.

Parametrized via env vars:
    LMARCH_MODAL_GPU   Modal GPU string (default "H100")
    LMARCH_MODAL_APP   Modal app name

Deploy:  modal deploy harness/modal_app.py
"""
from __future__ import annotations

import os
import pathlib

GPU = os.environ.get("LMARCH_MODAL_GPU", "H100")
APP_NAME = os.environ.get("LMARCH_MODAL_APP", "nanoslm-hybrid-arch-design")
REMOTE_TASK = "/opt/nanoslm_arch/task"

_PROBLEM_DIR = pathlib.Path(__file__).resolve().parent.parent

def _ver(mod):
    """Version string as a PLAIN str.

    str() is required, not cosmetic: torch.__version__ is a
    torch.torch_version.TorchVersion -- a str SUBCLASS defined inside torch --
    so returning it raw makes the whole result unpicklable on a client without
    torch:  DeserializationError: 'torch' module is not available.
    The judge is deliberately CPU-only and has no torch.
    """
    try:
        return str(__import__(mod).__version__)
    except Exception as exc:
        return f"<{type(exc).__name__}>"


try:
    import modal

    image = (
        modal.Image.debian_slim(python_version="3.11")
        # torch wheels bundle the CUDA runtime, so no nvidia/cuda base and no
        # nvcc are needed -- the whole reason this image builds in ~1 min.
        .pip_install("torch==2.6.0", "numpy<2")

        # flash-linear-attention: REQUIRED, not an optimization. PyTorch ships a
        # fused kernel for softmax attention (SDPA/flash) but none for linear or
        # recurrent mixers, so a hand-written GDN is unfused eager code. Measured
        # at ctx 8192: chunkwise did 6% of attention's FLOPs and still ran 3.5x
        # slower (11 optimizer steps vs 38). Under a fixed WALL-CLOCK budget that
        # makes the comparison "fused kernel vs unfused kernel" rather than
        # "architecture vs architecture", and a hybrid can never win.
        #
        # torch 2.6.0 (not 2.5.1) because fla warns it needs Triton >= 3.2.0 and
        # 2.5.1 ships 3.1.0 -- on 3.1.0 every GatedDeltaNet call hung 30+ min.
        #
        # fla 0.5.1 (not 0.4.1): on 0.4.1 the FORWARD compiled fine but the
        # BACKWARD did not --
        #   fla/ops/gated_delta_rule/wy_fast.py:303 prepare_wy_repr_bwd
        #   -> triton make_ttgir -> RuntimeError: PassManager::run failed
        # i.e. 0.4.1's backward kernels predate Triton 3.2's IR. This cost three
        # wrong guesses (head count twice) because an early probe timed FORWARD
        # ONLY and looked healthy; always exercise fwd+bwd when validating a
        # fused kernel.
        .pip_install("flash-linear-attention==0.5.1", "transformers==4.46.3")
        # Ship the problem directory itself: harness/, evaluator.py,
        # reference.py. The GPU function calls the real evaluator, so what runs
        # remotely is byte-identical to what Harbor runs.
        .add_local_dir(
            _PROBLEM_DIR, REMOTE_TASK, copy=True,
            ignore=["__pycache__", "*.pyc", ".git", "docker"],
        )
        .env({
            "PYTHONPATH": REMOTE_TASK,
            # MUST be set before the first CUDA call, so it belongs in the image
            # env -- setting it inside the function is too late. settings.py
            # declares this value but nothing was exporting it, so the Modal path
            # ran with torch.use_deterministic_algorithms(True) while cuBLAS was
            # still free to be non-deterministic (visible as a UserWarning in the
            # container log). CRN pairing depends on this.
            "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
            # fla's Triton kernels JIT-compile and autotune on first use. Give
            # them a writable cache so a warm container does not pay it twice.
            "TRITON_CACHE_DIR": "/tmp/triton-cache",
            # Reduce allocator fragmentation for the large fp32-logits CE at
            # ctx 8192 (paired with the batch_size=2 fix in settings.py).
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        })
    )

    app = modal.App(APP_NAME)

    # Real corpus (FineWeb-Edu, dolma2-tokenized) staged on a Modal Volume and
    # mounted at the data path harness/settings.py expects, so the GPU arms train
    # on REAL tokens instead of data.py's synthetic fallback. Populated once via
    # `modal volume put nanoslm-corpus {train,val}.bin manifest.json /`. This is
    # the "real shard mounted for calibration" the design leaves as a TODO.
    CORPUS_VOL = modal.Volume.from_name("nanoslm-corpus", create_if_missing=True)
    REMOTE_DATA = "/opt/nanoslm_arch/data"

    @app.function(image=image, gpu=GPU, timeout=6 * 60 * 60,
                  volumes={REMOTE_DATA: CORPUS_VOL})
    def evaluate_remote(solution_source: str, smoke: bool = True,
                        role: str = "final", overrides: dict | None = None) -> dict:
        """Run the judge on `solution_source` and return its full result.

        `solution_source` travels as TEXT, not a path: the submission is written
        into a scratch file remotely, exactly as the judge receives it.
        """
        import json
        import sys
        import tempfile
        import time

        sys.path.insert(0, REMOTE_TASK)

        os.environ["FRONTIER_NANOSLM_SMOKE"] = "1" if smoke else "0"
        os.environ["FRONTIER_NANOSLM_ROLE"] = role
        for k, v in (overrides or {}).items():
            os.environ[k] = str(v)

        import torch

        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None

        # Record the actual stack in every result. Version drift between what a
        # Dockerfile pins and what a warm container runs has already produced
        # two misleading results in this task's history.
        def _ver(mod):  # noqa: F811  (module-level _ver is the shared one)
            # str() is REQUIRED, not cosmetic. torch.__version__ is a
            # torch.torch_version.TorchVersion (a str SUBCLASS defined inside
            # torch), so returning it raw makes the whole result unpicklable on
            # any client without torch installed:
            #   DeserializationError: 'torch' module is not available
            # The judge/caller is deliberately CPU-only and has no torch, so
            # every value crossing this boundary must be a plain builtin.
            try:
                return str(__import__(mod).__version__)
            except Exception as exc:
                return f"<{type(exc).__name__}>"

        stack = {"torch": _ver("torch"), "triton": _ver("triton"), "fla": _ver("fla")}

        import evaluator  # noqa: E402  (must follow the env setup above)

        with tempfile.TemporaryDirectory() as td:
            sub = pathlib.Path(td) / "model.py"
            sub.write_text(solution_source)

            # DEBUG PATH (operator-only, never reachable from a submission):
            # rerun the arm OUTSIDE the evaluator's guard so the real traceback
            # survives. evaluator.py deliberately collapses every training
            # exception to "training runtime error: RuntimeError" for black-box
            # safety -- correct for agents, useless for debugging the harness.
            if overrides and overrides.get("DEBUG_TRACEBACK"):
                import traceback as _tb

                from harness import runner, settings as _s
                from harness.data import TokenData

                cfg = _s.active_config()
                try:
                    mod = evaluator._load_submission_module(str(sub))
                    runner.run_arm(runner.load_factory(mod), TokenData(cfg), cfg, "cuda")
                    # `stack` on the SUCCESS branch too. It was only on the
                    # failure branch, so a passing run could not be attributed
                    # to a version -- exactly the warm-container trap that
                    # already produced one stale, misread result here.
                    return {"debug": "submission arm completed without error",
                            "stack": stack}
                except Exception:
                    return {"debug_traceback": _tb.format_exc()[-4000:], "stack": stack}

            t0 = time.perf_counter()
            score, unbounded, message, metrics = evaluator.evaluate(str(sub))
            wall = time.perf_counter() - t0

        return {
            "score": score,
            "score_unbounded": unbounded,
            "message": message,
            "metrics": json.loads(json.dumps(metrics, default=str)),
            "wall_seconds": round(wall, 2),
            "gpu": gpu_name,
            "cuda_available": gpu_name is not None,
            "stack": stack,
        }

    @app.function(image=image, gpu=GPU, timeout=6 * 60 * 60,
                  volumes={REMOTE_DATA: CORPUS_VOL})
    def run_pair_remote(solution_source: str, smoke: bool = False,
                        role: str = "final") -> dict:
        """Run BOTH arms on one GPU and return their metrics as plain dicts.

        This is the entrypoint the JUDGE uses. It deliberately returns ARM
        METRICS, not a score: scoring stays judge-side so the scoring code and
        the hidden constants (bpb_score_scale) never ship to a GPU worker, and so the
        judge cannot be handed a score it did not compute.

        Contrast with evaluate_remote(), which runs the whole evaluator
        remotely -- useful for manual testing, but circular now that
        evaluator.evaluate() dispatches here.

        Everything crossing this boundary must be a plain builtin: the judge
        container is CPU-only and has no torch, so e.g. torch.__version__
        (a str SUBCLASS defined in torch) would make the result unpicklable.
        """
        import sys
        import tempfile

        sys.path.insert(0, REMOTE_TASK)
        os.environ["FRONTIER_NANOSLM_SMOKE"] = "1" if smoke else "0"
        os.environ["FRONTIER_NANOSLM_ROLE"] = role

        import torch  # noqa: F401  (ensures CUDA init before harness import)

        import evaluator  # noqa: F401  (sets CUBLAS_WORKSPACE_CONFIG early)
        from harness import runner, settings as _s

        cfg = _s.active_config()
        with tempfile.TemporaryDirectory() as td:
            sub = pathlib.Path(td) / "model.py"
            sub.write_text(solution_source)
            mod = evaluator._load_submission_module(str(sub))
            base, cand = runner.run_pair(mod, cfg, "cuda")

        def _arm(a):
            # Every value here must be a PLAIN builtin -- the judge is CPU-only
            # and has no torch, so anything torch-defined is unpicklable there.
            return {
                "val_bpb": float(a.val_bpb),
                "val_ppl": float(a.val_ppl),
                "steps": int(a.steps),
                "wall_seconds": float(a.wall_seconds),
                "n_params": int(a.n_params),
                # Context this arm TRAINED at. The baseline is always 8192;
                # a submission may declare a shorter one via BLOCK_SIZE. Both
                # arms are always EVALUATED at cfg.eval_block_size (8192).
                "train_block_size": int(a.train_block_size),
                # Warmup is where Triton JIT is supposed to land. If
                # warmup_error is non-empty, warmup silently no-opped and its
                # cost was deferred INTO the timed loop -- the exact failure
                # that produced sub_steps=1 at 103.2s.
                "warmup_seconds": float(a.warmup_seconds),
                "warmup_error": str(a.warmup_error),
            }

        return {
            "baseline": _arm(base),
            "submission": _arm(cand),
            # FIXED scoring window, reported so a result is self-describing:
            # both arms' val_bpb come from windows of exactly this width.
            "eval_block_size": int(cfg.eval_block_size),
            # Bump on every behavioral change to this file. A deploy does NOT
            # evict warm containers, so the first call after `modal deploy` can
            # still execute the OLD code -- this has produced misleading results
            # twice in this task's history. Check this value before trusting a
            # result.
            "code_version": "agent-train-ctx-v5",
            "stack": {"torch": str(torch.__version__),
                      "triton": _ver("triton"), "fla": _ver("fla")},
        }


except ImportError:  # modal absent (e.g. CPU-only unit-test host)
    app = None

"""Modal app: run the nanoslm_hybrid_arch_design judge on one GPU.

Mirrors the GPU-on-Modal pattern of vllm_llm_serving_optimization and nanowm:
the judge container stays CPU-only and calls into a Modal GPU function.

Two things make this app much lighter than lm_arch_discovery's:

  * No external repo and no CUDA source build. The harness is self-contained
    PyTorch; the only third-party imports across harness/*.py are torch and
    numpy. torch's own wheels ship the CUDA runtime, so a slim base works and
    the image builds in ~1 min rather than needing nvcc.
  * No dataset download and no gated tokenizer. The corpus is pre-tokenized by
    docker/prep_assets.py with dolma2 (allenai/dolma2-tokenizer, 100278 ids,
    model vocab padded to 100352 --
    ungated, no HF token), so this image never tokenizes anything. The real
    train.bin/val.bin/manifest.json are mounted from the nanoslm-corpus Modal
    Volume (below); the harness requires them and raises DataError rather than
    synthesizing tokens, so every reported bits-per-byte is a real measurement.

Rather than reimplement the training loop here, this calls evaluator.evaluate()
-- the same entrypoint Harbor calls -- so there is no second code path to drift.

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

# Function timeout must clear a full final-role pair: two arms trained back-to-
# back (~6 h each = 12 h normally, up to the 12 h hard cap each in the worst
# case), plus warmup and both evals. Set to Modal's 24 h maximum for the widest
# margin. (The old 6 h could not finish even one 6 h arm.)
FN_TIMEOUT_SECONDS = 24 * 60 * 60

_PROBLEM_DIR = pathlib.Path(__file__).resolve().parent.parent

def _ver(mod):
    """Version string as a plain str.

    str() is required, not cosmetic: torch.__version__ is a
    torch.torch_version.TorchVersion -- a str subclass defined inside torch --
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

        # flash-linear-attention: required, not an optimization. PyTorch ships a
        # fused kernel for softmax attention (SDPA/flash) but none for linear or
        # recurrent mixers, so a hand-written GDN is unfused eager code. Under a
        # fixed wall-clock budget that would make the comparison "fused vs unfused
        # kernel" rather than "architecture vs architecture", and a hybrid could
        # never win.
        #
        # torch 2.6.0 (not 2.5.1) for Triton >= 3.2.0, which fla requires; on the
        # Triton 3.1.0 that torch 2.5.1 ships, GatedDeltaNet calls hung.
        #
        # fla 0.5.1 (not 0.4.1): on 0.4.1 the forward compiled fine but the
        # Backward did not --
        #   fla/ops/gated_delta_rule/wy_fast.py:303 prepare_wy_repr_bwd
        #   -> triton make_ttgir -> RuntimeError: PassManager::run failed
        # i.e. 0.4.1's backward kernels predate Triton 3.2's IR. This cost three
        # wrong guesses (head count twice) because an early probe timed forward
        # Only and looked healthy; always exercise fwd+bwd when validating a
        # fused kernel.
        .pip_install("flash-linear-attention==0.5.1", "transformers==4.46.3")
        # Operator-only observability (train._maybe_init_wandb). Inert unless a
        # call passes FRONTIER_NANOSLM_WANDB=1 via `overrides`, so scored runs
        # and the baseline cache are unaffected.
        .pip_install("wandb")
        # Ship the problem directory itself: harness/, evaluator.py,
        # reference.py. The GPU function calls the real evaluator, so what runs
        # remotely is byte-identical to what Harbor runs. `.assets` is the
        # LOCAL dev staging (gigabytes of tokens, and a stale val split) -- the
        # real corpus mounts from the Volume, so shipping it was pure deploy
        # bloat plus an unguarded token-stream copy in the container.
        .add_local_dir(
            _PROBLEM_DIR, REMOTE_TASK, copy=True,
            ignore=["__pycache__", "*.pyc", ".git", "docker", ".assets"],
        )
        .env({
            "PYTHONPATH": REMOTE_TASK,
            # Must be set before the first CUDA call, so it belongs in the image
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
            # Keep wandb's scratch out of the shipped task tree.
            "WANDB_DIR": "/tmp/wandb",
        })
    )

    app = modal.App(APP_NAME)

    # WANDB_API_KEY for the opt-in observability path. The secret must exist
    # for deploys to resolve (create once:
    #   modal secret create wandb WANDB_API_KEY=...
    # ); a placeholder value just means wandb.init fails and logging silently
    # stays off -- training is untouched either way.
    WANDB_SECRET = modal.Secret.from_name("wandb")

    # Real corpus (FineWeb-Edu, dolma2-tokenized) staged on a Modal Volume and
    # mounted at the data path harness/settings.py expects, so the GPU arms train
    # on real tokens. The harness has no synthetic fallback, so this mount is
    # required. Populated once via
    # `modal volume put nanoslm-corpus {train,val}.bin manifest.json /`.
    CORPUS_VOL = modal.Volume.from_name("nanoslm-corpus", create_if_missing=True)
    REMOTE_DATA = "/opt/nanoslm_arch/data"

    @app.function(image=image, gpu=GPU, timeout=FN_TIMEOUT_SECONDS,
                  volumes={REMOTE_DATA: CORPUS_VOL}, secrets=[WANDB_SECRET])
    def evaluate_remote(solution_source: str,
                        role: str = "final", overrides: dict | None = None) -> dict:
        """Run the judge on `solution_source` and return its full result.

        `solution_source` travels as text, not a path: the submission is written
        into a scratch file remotely, exactly as the judge receives it.
        """
        import json
        import sys
        import tempfile
        import time

        sys.path.insert(0, REMOTE_TASK)

        os.environ["FRONTIER_NANOSLM_ROLE"] = role
        for k, v in (overrides or {}).items():
            os.environ[k] = str(v)

        import torch

        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None

        # Record the actual stack in every result. Version drift between what a
        # Dockerfile pins and what a warm container runs has already produced
        # two misleading results in this task's history.
        def _ver(mod):  # noqa: F811  (module-level _ver is the shared one)
            # str() is required, not cosmetic. torch.__version__ is a
            # torch.torch_version.TorchVersion (a str subclass defined inside
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

            # Debug path (operator-only, never reachable from a submission):
            # rerun the arm outside the evaluator's guard so the real traceback
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
                    # `stack` on the success branch too. It was only on the
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

    # Bump on every behavioral change to this file OR to the harness it ships
    # (add_local_dir above). Two reasons, both learned the hard way:
    #   * A deploy does not evict warm containers, so the first call after
    #     `modal deploy` can still execute the old code -- this has produced
    #     misleading results twice in this task's history. Check this value
    #     before trusting a result.
    #   * It is part of the baseline-cache key. The config fingerprint hashes
    #     config VALUES only, so a harness behavior change (e.g. the LR
    #     schedule moving from step-based to wall-clock decay) changes the
    #     baseline's val_bpb without changing the fingerprint. Keying the cache
    #     by fingerprint alone would then pair fresh submissions against a
    #     stale baseline.
    CODE_VERSION = "final-6h-agentcache-v8"

    # Baseline cache for the agent role, on the corpus Volume so it survives
    # containers (the container FS is ephemeral; settings.baseline_cache_path
    # is the local-backend location and is NOT mounted here).
    BASELINE_CACHE = f"{REMOTE_DATA}/baseline/baseline_arm.json"

    @app.function(image=image, gpu=GPU, timeout=FN_TIMEOUT_SECONDS,
                  volumes={REMOTE_DATA: CORPUS_VOL}, secrets=[WANDB_SECRET])
    def run_pair_remote(solution_source: str,
                        role: str = "final",
                        overrides: dict | None = None) -> dict:
        """Run the arms on one GPU and return their metrics as plain dicts.

        This is the entrypoint the judge uses. It deliberately returns arm
        Metrics, not a score: scoring stays judge-side so the scoring code and
        no score constant ships to a GPU worker, and so the
        judge cannot be handed a score it did not compute.

        Role semantics (this is what makes iteration affordable):

          final  fresh baseline + submission CRN pair on this GPU (~2T).
                 Authoritative. Opportunistically refreshes the baseline cache.
          agent  cheap iterative feedback: reuse the baseline cached on the
                 corpus Volume (keyed by config fingerprint + CODE_VERSION) and
                 train only the submission (~T). A cache miss falls back to the
                 full pair and populates the cache, so only the first agent
                 call after a deploy/config change pays ~2T.

        Guard rejections come back as {"guard_error": ...} rather than raised:
        GuardError is defined in harness.runner, which imports torch, so the
        CPU-only judge could not deserialize the exception -- and the public
        guard message (param cap, BLOCK_SIZE range, eval-shape failure) is
        exactly the feedback an iterating agent needs.

        Everything crossing this boundary must be a plain builtin: the judge
        container is CPU-only and has no torch, so e.g. torch.__version__
        (a str subclass defined in torch) would make the result unpicklable.
        """
        import json
        import sys
        import tempfile

        sys.path.insert(0, REMOTE_TASK)
        os.environ["FRONTIER_NANOSLM_ROLE"] = role
        # Operator-only env passthrough (e.g. FRONTIER_NANOSLM_WANDB=1). The
        # judge never passes overrides, so the scored path is unchanged.
        for k, v in (overrides or {}).items():
            os.environ[k] = str(v)

        import torch  # noqa: F401  (ensures CUDA init before harness import)

        import evaluator  # noqa: F401  (sets CUBLAS_WORKSPACE_CONFIG early)
        from harness import runner, settings as _s
        from harness.data import TokenData

        cfg = _s.active_config()
        # The corpus identity is part of the key: the config fingerprint hashes
        # dataset_name but not the staged shard's SIZE, and restaging a larger
        # shard changes the sampled windows (data.batch draws offsets against
        # train.size) -- so a baseline trained on the old shard must not be
        # paired with submissions trained on the new one. The on-disk byte size
        # is a cheap, sufficient stamp for that.
        try:
            corpus_stamp = str(os.path.getsize(cfg.train_tokens_path))
        except OSError:
            corpus_stamp = "nocorpus"
        cache_key = f"{_s.config_fingerprint(cfg)}:{corpus_stamp}:{CODE_VERSION}"
        cache_path = pathlib.Path(BASELINE_CACHE)

        def _arm(a):
            # Every value here must be a plain builtin -- the judge is CPU-only
            # and has no torch, so anything torch-defined is unpicklable there.
            return {
                "val_bpb": float(a.val_bpb),
                "val_ppl": float(a.val_ppl),
                "steps": int(a.steps),
                "wall_seconds": float(a.wall_seconds),
                "n_params": int(a.n_params),
                # Context this arm trained at. The baseline is always 8192;
                # a submission may declare a shorter one via BLOCK_SIZE. Both
                # arms are always evaluated at cfg.eval_block_size (8192).
                "train_block_size": int(a.train_block_size),
                # Warmup is where Triton JIT is supposed to land. If
                # warmup_error is non-empty, warmup silently no-opped and its
                # cost was deferred into the timed loop -- a step-0 stall. These
                # fields surface that regression.
                "warmup_seconds": float(a.warmup_seconds),
                "warmup_error": str(a.warmup_error),
            }

        def _cache_read():
            """Cached baseline arm dict for this key, or None. Best-effort."""
            try:
                CORPUS_VOL.reload()   # see commits from other containers
            except Exception:
                pass
            try:
                entry = json.loads(cache_path.read_text()).get(cache_key)
                # Sanity: a valid entry is an arm dict with a positive bpb.
                if isinstance(entry, dict) and float(entry.get("val_bpb", 0)) > 0:
                    return entry
            except Exception:
                pass
            return None

        def _cache_write(entry: dict) -> None:
            """Best-effort persist; a failure only costs the next call ~T."""
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    data = json.loads(cache_path.read_text())
                    if not isinstance(data, dict):
                        data = {}
                except Exception:
                    data = {}
                data[cache_key] = entry
                cache_path.write_text(json.dumps(data))
                CORPUS_VOL.commit()
            except Exception:
                pass

        base_info = _cache_read() if role == "agent" else None
        baseline_cached = base_info is not None

        with tempfile.TemporaryDirectory() as td:
            sub = pathlib.Path(td) / "model.py"
            sub.write_text(solution_source)
            mod = evaluator._load_submission_module(str(sub))
            try:
                if base_info is None:
                    # final role, or first agent call for this key: full CRN
                    # pair, then persist the baseline for future agent calls.
                    base, cand = runner.run_pair(mod, cfg, "cuda")
                    base_info = _arm(base)
                    _cache_write(base_info)
                else:
                    # agent role, cache hit: submission arm only (~T). Resolve
                    # (and range-guard) BLOCK_SIZE before anything expensive,
                    # exactly as run_pair does.
                    sub_block = runner.resolve_train_block_size(mod, cfg)
                    data = TokenData(cfg)
                    cand = runner.run_arm(
                        runner.load_factory(mod), data, cfg, "cuda", sub_block,
                        run_label="submission",
                    )
            except runner.GuardError as exc:
                return {
                    "guard_error": str(exc),
                    "code_version": CODE_VERSION,
                    "stack": {"torch": str(torch.__version__),
                              "triton": _ver("triton"), "fla": _ver("fla")},
                }

        return {
            "baseline": base_info,
            "submission": _arm(cand),
            "baseline_cached": baseline_cached,
            # Fixed scoring window, reported so a result is self-describing:
            # both arms' val_bpb come from windows of exactly this width.
            "eval_block_size": int(cfg.eval_block_size),
            "code_version": CODE_VERSION,
            "stack": {"torch": str(torch.__version__),
                      "triton": _ver("triton"), "fla": _ver("fla")},
        }


except ImportError:  # modal absent (e.g. CPU-only unit-test host)
    app = None

"""Modal app that serves a (patched or vanilla) vLLM build on Modal H100 GPU(s).

This module is deployed with ``modal deploy serving_eval/modal_app.py``. It is
parametrized entirely through environment variables so the same module serves
both the baseline (clean) and patched source trees, under distinct app names:

    VLLM_SERVING_SRC   absolute path to the vLLM source tree to build from
    VLLM_SERVING_MODEL HuggingFace model id to serve
    VLLM_SERVING_GPU   Modal GPU string, "H100:N" for N-way TP (default "H100:2")
    VLLM_SERVING_APP   Modal app name (must be unique per concurrent server)
    VLLM_SERVING_LABEL deterministic web label for a predictable URL
    VLLM_SERVING_SCALEDOWN  idle seconds before the GPU container is released
    VLLM_SERVING_STARTUP    seconds Modal waits for the server port to open
    VLLM_SERVING_MAXLEN     vLLM --max-model-len
    VLLM_SERVING_HF_SECRET  name of the Modal Secret holding HF_TOKEN
    VLLM_SERVING_VERSION    pinned vLLM version for setuptools_scm (default 0.11.0)
    VLLM_SERVING_PRECOMPILED_WHEEL  ABI-matched precompiled wheel URL to overlay
    VLLM_SERVING_TRANSFORMERS        pinned transformers requirement spec

The build uses VLLM_USE_PRECOMPILED=1 so only vLLM's Python layer is rebuilt
from source; the prebuilt CUDA kernels are reused. This keeps per-submission
image builds to minutes and enforces the task's Python-only patch policy.
"""

from __future__ import annotations

import os

import modal

VLLM_SERVING_SRC = os.environ.get("VLLM_SERVING_SRC", "/opt/vllm-clean")
VLLM_SERVING_MODEL = os.environ.get("VLLM_SERVING_MODEL", "Qwen/Qwen3-Coder-30B-A3B-Instruct")
VLLM_SERVING_GPU = os.environ.get("VLLM_SERVING_GPU", "H100:2")
VLLM_SERVING_APP = os.environ.get("VLLM_SERVING_APP", "vllm-serving-opt")
VLLM_SERVING_LABEL = os.environ.get("VLLM_SERVING_LABEL", VLLM_SERVING_APP)
VLLM_SERVING_SCALEDOWN = int(os.environ.get("VLLM_SERVING_SCALEDOWN", "900"))
VLLM_SERVING_STARTUP = int(os.environ.get("VLLM_SERVING_STARTUP", "1200"))
# 32K context fits comfortably on H100s (80GB each) and avoids the growing
# multi-turn conversation overflowing the window (which 404'd mid-run on a
# smaller 16K setup). Lower this if serving on a smaller card.
VLLM_SERVING_MAXLEN = int(os.environ.get("VLLM_SERVING_MAXLEN", "32768"))
VLLM_SERVING_HF_SECRET = os.environ.get("VLLM_SERVING_HF_SECRET", "huggingface-secret")
# Pinned vLLM version. The source tree is copied into the build image, where its
# git metadata is not reliably readable by setuptools_scm (and a patched tree is
# "dirty" anyway), so the version is provided explicitly to make the editable
# install deterministic and independent of git state.
VLLM_SERVING_VERSION = os.environ.get("VLLM_SERVING_VERSION", "0.11.0")
# ABI-matched precompiled wheel for the pinned version. With VLLM_USE_PRECOMPILED,
# vLLM's build picks the wheel by deriving a base commit from git; for a shallow/
# detached source tree that derivation fails and it falls back to a *nightly*
# wheel, whose compiled extensions are ABI-incompatible with the pinned source
# and abort at engine init (std::bad_alloc). Pin the matching release wheel so the
# overlaid .so files match the source.
VLLM_SERVING_PRECOMPILED_WHEEL = os.environ.get(
    "VLLM_SERVING_PRECOMPILED_WHEEL",
    "https://files.pythonhosted.org/packages/47/33/"
    "d19e0763c34392ec956534536fa837c060495bfff31ed83452135ea7608d/"
    "vllm-0.11.0-cp38-abi3-manylinux1_x86_64.whl",
)
# vLLM 0.11.0 only lower-bounds transformers (>=4.55.2); pin the CI-tested version
# so the resolver does not pull transformers 5.x (incompatible tokenizer API).
VLLM_SERVING_TRANSFORMERS = os.environ.get("VLLM_SERVING_TRANSFORMERS", "transformers==4.55.2")
VLLM_PORT = 8000
REMOTE_SRC = "/src/vllm"

# Persisted caches so weights are downloaded once and reused across cold starts.
hf_cache_vol = modal.Volume.from_name("vllm-serving-opt-hf-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-serving-opt-vllm-cache", create_if_missing=True)

serving_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .apt_install("git", "build-essential")
    .pip_install("uv")
    # Bake the source tree into the image at build time. copy=True is required
    # because the next build step (editable install) runs against these files.
    .add_local_dir(VLLM_SERVING_SRC, REMOTE_SRC, copy=True)
    .run_commands(
        # SETUPTOOLS_SCM_PRETEND_VERSION* bypasses git-based version detection,
        # which fails for the copied (and possibly patched/dirty) source tree.
        # VLLM_PRECOMPILED_WHEEL_LOCATION pins the ABI-matched release wheel (the
        # default nightly fallback aborts at engine init). transformers is pinned
        # to the CI-tested version; hf_transfer backs HF_HUB_ENABLE_HF_TRANSFER.
        f"cd {REMOTE_SRC} && "
        f"SETUPTOOLS_SCM_PRETEND_VERSION_FOR_VLLM={VLLM_SERVING_VERSION} "
        f"SETUPTOOLS_SCM_PRETEND_VERSION={VLLM_SERVING_VERSION} "
        f"VLLM_PRECOMPILED_WHEEL_LOCATION={VLLM_SERVING_PRECOMPILED_WHEEL} "
        f"VLLM_USE_PRECOMPILED=1 uv pip install --system -e . "
        f"'{VLLM_SERVING_TRANSFORMERS}' hf_transfer",
    )
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "DO_NOT_TRACK": "1",
            # These are read inside serve(), which runs in the REMOTE container
            # where the deploy-time process env is NOT present. Bake the values
            # into the image env (evaluated here at deploy time) so the remote
            # serve() sees the requested model / context / GPU spec instead of
            # silently falling back to the module-level defaults.
            "VLLM_SERVING_MODEL": VLLM_SERVING_MODEL,
            "VLLM_SERVING_MAXLEN": str(VLLM_SERVING_MAXLEN),
            "VLLM_SERVING_GPU": VLLM_SERVING_GPU,
        }
    )
)

app = modal.App(VLLM_SERVING_APP)


def _hf_secrets() -> list[modal.Secret]:
    try:
        return [modal.Secret.from_name(VLLM_SERVING_HF_SECRET)]
    except Exception:
        return []


@app.function(
    image=serving_image,
    gpu=VLLM_SERVING_GPU,
    # Pin to a SINGLE serving container. Without this, Modal autoscales out under
    # load (spinning up more GPU replicas), which relieves exactly the
    # queueing/preemption pressure the scheduler optimization is supposed to
    # manage — making the latency signal vanish. One container = all load lands on
    # one GPU set, so contention (and thus scheduling) is real and measurable.
    max_containers=1,
    scaledown_window=VLLM_SERVING_SCALEDOWN,
    timeout=24 * 60 * 60,
    secrets=_hf_secrets(),
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=VLLM_PORT, startup_timeout=VLLM_SERVING_STARTUP, label=VLLM_SERVING_LABEL)
def serve() -> None:
    import subprocess

    # Derive tensor-parallel size from the Modal GPU spec ("H100" -> 1,
    # "H100:2" -> 2). With more than one GPU, vLLM must shard across them.
    gpu_count = 1
    if ":" in VLLM_SERVING_GPU:
        try:
            gpu_count = max(1, int(VLLM_SERVING_GPU.split(":", 1)[1]))
        except ValueError:
            gpu_count = 1

    cmd = [
        "vllm",
        "serve",
        VLLM_SERVING_MODEL,
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
        "--max-model-len",
        str(VLLM_SERVING_MAXLEN),
        "--disable-log-requests",
    ]
    if gpu_count > 1:
        cmd += ["--tensor-parallel-size", str(gpu_count)]
    subprocess.Popen(" ".join(cmd), shell=True)

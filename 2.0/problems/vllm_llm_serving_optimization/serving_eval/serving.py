"""Deploy, health-check, and tear down a Modal-hosted vLLM server.

The judge and the public test both build a Modal image from a vLLM source tree
and serve it on an H100. This module wraps that lifecycle:

    deploy_server(...)  -> ServerHandle(base_url, app_name)
    wait_healthy(...)
    stop_server(...)

Deployment shells out to the ``modal`` CLI in a fresh process whose environment
selects the source tree / model / app name (see modal_app.py). The public URL
is then resolved through the Modal SDK.
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

MODAL_APP_MODULE = str(Path(__file__).with_name("modal_app.py"))

# Substrings that mark a transient Modal control-plane / build failure (image
# build evicted, app stopped mid-deploy, gateway timeout) rather than a real
# build error in the patched source. These are safe to retry.
_TRANSIENT_MODAL_MARKERS = (
    "external shut-down",
    "terminated due to external",
    "please try again",
    "app_state_stopped",
    "conflicterror",
    "eat_timeout",
    "deadline exceeded",
    "connection reset",
    "502 bad gateway",
    "503 service",
    "temporarily unavailable",
    "timed out",
)


def _is_transient_modal_error(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _TRANSIENT_MODAL_MARKERS)


@dataclass
class ServerHandle:
    base_url: str  # OpenAI base, e.g. https://...modal.run/v1
    app_name: str
    label: str


class ServingError(RuntimeError):
    pass


def _server_env(
    *,
    src_path: str,
    model: str,
    gpu: str,
    app_name: str,
    label: str,
    scaledown_seconds: int,
    startup_timeout_seconds: int,
) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "VLLM_SERVING_SRC": src_path,
            "VLLM_SERVING_MODEL": model,
            "VLLM_SERVING_GPU": gpu,
            "VLLM_SERVING_APP": app_name,
            "VLLM_SERVING_LABEL": label,
            "VLLM_SERVING_SCALEDOWN": str(scaledown_seconds),
            "VLLM_SERVING_STARTUP": str(startup_timeout_seconds),
        }
    )
    return env


def _resolve_web_url(app_name: str) -> str:
    import modal

    fn = modal.Function.from_name(app_name, "serve")
    url = fn.get_web_url()
    if not url:
        raise ServingError("deployed Modal function does not expose a web URL")
    return url.rstrip("/")


def deploy_server(
    *,
    src_path: str,
    model: str,
    gpu: str,
    app_name: str,
    label: str,
    scaledown_seconds: int,
    startup_timeout_seconds: int,
    build_timeout_seconds: int,
    deploy_retries: int = 3,
) -> ServerHandle:
    env = _server_env(
        src_path=src_path,
        model=model,
        gpu=gpu,
        app_name=app_name,
        label=label,
        scaledown_seconds=scaledown_seconds,
        startup_timeout_seconds=startup_timeout_seconds,
    )
    # Modal's control plane / image builder occasionally evicts a build under load
    # (concurrent deploys, transient gateway errors). Those failures are unrelated
    # to the patched source, so retry them with a short backoff; a genuine build
    # error in the patch is non-transient and fails fast.
    attempts = max(1, deploy_retries)
    last_error = "modal deploy failed"
    for attempt in range(1, attempts + 1):
        try:
            subprocess.run(
                ["modal", "deploy", MODAL_APP_MODULE],
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=build_timeout_seconds,
            )
            base = _resolve_web_url(app_name)
            return ServerHandle(base_url=f"{base}/v1", app_name=app_name, label=label)
        except subprocess.TimeoutExpired:
            last_error = "modal deploy timed out"
            transient = True
        except subprocess.CalledProcessError as exc:
            # Surface only a short, sanitized tail; build logs may contain paths.
            tail = (exc.stderr or exc.stdout or "")[-600:]
            last_error = f"modal deploy failed: {tail}"
            transient = _is_transient_modal_error(tail)
        except ServingError as exc:
            # _resolve_web_url failed (app not fully registered yet) — treat as transient.
            last_error = str(exc)
            transient = True

        if not transient or attempt == attempts:
            raise ServingError(last_error)

        # Clear any half-created/stopped app state, then back off before retrying.
        try:
            subprocess.run(
                ["modal", "app", "stop", app_name],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception:
            pass
        time.sleep(min(45, 10 * attempt))

    raise ServingError(last_error)


def wait_healthy(handle: ServerHandle, *, model: str, timeout_seconds: int) -> None:
    """Block until the server answers /v1/models, or raise on timeout."""
    deadline = time.time() + timeout_seconds
    models_url = f"{handle.base_url}/models"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            req = urllib.request.Request(models_url, headers={"Authorization": "Bearer EMPTY"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return  # server is up; auth shape differs
            last_error = exc
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(5)
    raise ServingError(f"server did not become healthy within {timeout_seconds}s: {last_error}")


def stop_server(app_name: str) -> None:
    try:
        subprocess.run(
            ["modal", "app", "stop", app_name],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception:
        # Best-effort teardown; idle containers also scale to zero on their own.
        pass

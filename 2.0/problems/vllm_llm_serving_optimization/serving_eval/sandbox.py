"""Per-instance shell sandbox for the agentic workload.

Each SWE-bench instance runs the agent's shell commands in an isolated sandbox
rooted at the repository working directory. Two backends are supported:

* ``docker``  – the SWE-bench per-instance testbed image
  (``swebench/sweb.eval.x86_64.<instance>``) with the repo checked out at
  ``/testbed``. This is the faithful backend used by the judge when a Docker
  daemon is reachable; it is also what makes a real resolve-rate possible.
* ``local``   – a lightweight temporary directory. Used for fast public-test
  feedback (and CI) where Docker-in-Docker is unavailable. Commands run on the
  host filesystem inside the temp dir.

Both backends expose the same ``run(cmd) -> (exit_code, output)`` and
``read_patch()`` interface so the agent loop is backend-agnostic.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            capture_output=True,
            timeout=20,
        )
        return True
    except Exception:
        return False


def swebench_image(instance_id: str) -> str:
    key = instance_id.lower().replace("__", "_1776_")
    return f"docker.io/swebench/sweb.eval.x86_64.{key}:latest"


class Sandbox:
    workdir = "/testbed"

    def run(self, command: str, *, timeout: int) -> tuple[int, str]:
        raise NotImplementedError

    def read_patch(self) -> str:
        raise NotImplementedError

    def close(self) -> None:
        pass


class DockerSandbox(Sandbox):
    def __init__(self, instance_id: str, *, command_timeout: int = 60) -> None:
        self.instance_id = instance_id
        self.command_timeout = command_timeout
        self.container = f"vllm-serving-opt-{uuid.uuid4().hex[:12]}"
        image = swebench_image(instance_id)
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                self.container,
                "--network",
                "none",
                "-w",
                self.workdir,
                image,
                "sleep",
                "infinity",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )

    def run(self, command: str, *, timeout: int) -> tuple[int, str]:
        try:
            proc = subprocess.run(
                ["docker", "exec", "-w", self.workdir, self.container, "bash", "-lc", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, "command timed out"
        except Exception as exc:  # noqa: BLE001
            # A dead/evicted container or a docker hiccup must not kill the whole
            # instance thread; surface it as a non-zero command result so the
            # agent loop (and per-instance latency) keep going.
            return 1, f"sandbox error: {type(exc).__name__}"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def read_patch(self) -> str:
        code, out = self.run("git add -A && git diff --cached", timeout=self.command_timeout)
        return out if code == 0 else ""

    def close(self) -> None:
        subprocess.run(["docker", "rm", "-f", self.container], check=False, capture_output=True)


class LocalSandbox(Sandbox):
    def __init__(self, instance_id: str) -> None:
        self.instance_id = instance_id
        self._dir = tempfile.mkdtemp(prefix="vllm-serving-opt-sandbox-")
        self.workdir = self._dir
        subprocess.run(["git", "init", "-q"], cwd=self._dir, check=False, capture_output=True)

    def run(self, command: str, *, timeout: int) -> tuple[int, str]:
        try:
            proc = subprocess.run(
                ["bash", "-lc", command],
                cwd=self._dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, "command timed out"
        except Exception as exc:  # noqa: BLE001
            return 1, f"sandbox error: {type(exc).__name__}"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def read_patch(self) -> str:
        code, out = self.run("git add -A && git diff --cached", timeout=60)
        return out if code == 0 else ""

    def close(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)


def make_sandbox(instance_id: str, *, prefer_docker: bool, command_timeout: int = 60) -> Sandbox:
    if prefer_docker and docker_available():
        try:
            return DockerSandbox(instance_id, command_timeout=command_timeout)
        except Exception:
            pass
    return LocalSandbox(instance_id)

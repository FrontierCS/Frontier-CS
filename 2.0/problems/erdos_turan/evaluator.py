"""Evaluator for the Erdos Turán 2.0 problem."""

from __future__ import annotations

import importlib.util
import math
import os
import pickle
import pwd
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

M_SIZE = 131072
BASELINE_SIZE = math.isqrt(M_SIZE)  # 362
TIMEOUT_SECONDS = 10800
SCORE_POWER = 3.0


def _protect_evaluator_source() -> None:
    """Hide evaluator source from unprivileged submitted solutions in containers."""
    try:
        evaluator_path = Path(__file__).resolve()
        if str(evaluator_path).startswith(("/judge/", "/tests/")) and os.geteuid() == 0:
            evaluator_path.chmod(0o600)
    except Exception:
        pass


_protect_evaluator_source()


def _solution_preexec():
    """Return a preexec_fn that runs submitted code as nobody when possible."""
    if os.name != "posix":
        return None
    try:
        if os.geteuid() != 0:
            return None
        nobody = pwd.getpwnam("nobody")
    except Exception:
        return None

    def demote() -> None:
        os.setgid(nobody.pw_gid)
        os.setuid(nobody.pw_uid)

    return demote


def _to_elements(raw: Any) -> list[int]:
    try:
        values = raw.tolist()
    except Exception:
        values = list(raw)

    elements: list[int] = []
    for index, item in enumerate(values):
        try:
            v = int(item)
        except Exception:
            raise ValueError(f"element {index} cannot be converted to int")
        elements.append(v)
    return elements


def _load_elements(solution_path: str) -> Any:
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import solution from {solution_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in ("solve", "generate_set", "run"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn(M_SIZE)

    elements = getattr(module, "ELEMENTS", None)
    if elements is not None:
        return elements

    raise RuntimeError("solution must define solve(m), generate_set(m), run(m), or ELEMENTS")


def _run_solution(solution_path: str) -> tuple[Any, str]:
    with tempfile.TemporaryDirectory(prefix="erdos_turan_") as tmp:
        tmp_path = Path(tmp)
        isolated_solution_path = tmp_path / "solution.py"
        result_path = tmp_path / "result.pkl"
        runner_path = tmp_path / "runner.py"
        shutil.copy2(solution_path, isolated_solution_path)
        runner_path.write_text(
            """
import importlib.util
import pickle
from pathlib import Path

solution_path = __SOLUTION_PATH__
result_path = Path(__RESULT_PATH__)
m_size = __M_SIZE__


def load_elements():
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in ("solve", "generate_set", "run"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn(m_size)

    elements = getattr(module, "ELEMENTS", None)
    if elements is not None:
        return elements

    raise RuntimeError("solution must define solve(m), generate_set(m), run(m), or ELEMENTS")

try:
    elements = load_elements()
    with result_path.open("wb") as f:
        pickle.dump({"elements": elements}, f)
except Exception:
    with result_path.open("wb") as f:
        pickle.dump({"error": "solution failed while generating elements"}, f)
""".replace("__SOLUTION_PATH__", repr(str(isolated_solution_path)))
            .replace("__RESULT_PATH__", repr(str(result_path)))
            .replace("__M_SIZE__", repr(M_SIZE)),
            encoding="utf-8",
        )
        preexec_fn = _solution_preexec()
        if preexec_fn is not None:
            nobody = pwd.getpwnam("nobody")
            os.chown(tmp, nobody.pw_uid, nobody.pw_gid)
            os.chown(isolated_solution_path, nobody.pw_uid, nobody.pw_gid)
            os.chown(runner_path, nobody.pw_uid, nobody.pw_gid)
        os.chmod(tmp, 0o700 if preexec_fn is not None else 0o755)

        proc = subprocess.run(
            [sys.executable, str(runner_path)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            preexec_fn=preexec_fn,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"solution runner exited with code {proc.returncode}")
        if not result_path.exists():
            raise RuntimeError("solution did not produce a result")
        with result_path.open("rb") as f:
            payload = pickle.load(f)
        if "error" in payload:
            raise RuntimeError("solution failed while generating elements")
        return payload["elements"], ""


def _validate_and_count(elements: list[int]) -> int:
    """Validate the element set and return its size. Raises ValueError on any violation."""
    seen: set[int] = set()
    for index, x in enumerate(elements):
        if not isinstance(x, int):
            raise ValueError(f"element {index} is not an integer")
        if x < 1 or x > M_SIZE:
            raise ValueError(f"element {index} = {x} is out of range [1, {M_SIZE}]")
        if x in seen:
            raise ValueError(f"duplicate element {x}")
        seen.add(x)

    _check_no_3ap(seen)
    return len(seen)


def _check_no_3ap(s: set[int]) -> None:
    """Raise ValueError if the set contains a 3-term arithmetic progression.

    Uses FFT-based convolution to detect 3-APs in O(M log M) time.

    Key insight: a 3-AP (a, b, c) satisfies a + c = 2b.  If we build an
    indicator vector f where f[x] = 1 when x ∈ S, then the self-convolution
    g = f * f gives:

        g[k] = number of ordered pairs (a, c) with a, c ∈ S and a + c = k

    For a candidate middle element b ∈ S we check g[2b]:
      - The pair (b, b) always contributes 1 to g[2b] (b + b = 2b).
      - Any other pair (a, c) with a ≠ b or c ≠ b and a + c = 2b would mean
        {a, b, c} is a 3-AP.  Such pairs come in symmetric pairs (a, c) and
        (c, a), each contributing 1, so an extra pair adds 2 to g[2b].
      - Therefore g[2b] > 1 (i.e. ≥ 3 in practice) signals a 3-AP with
        middle element b.

    We use a threshold of 1.5 instead of 1 to guard against floating-point
    rounding from the FFT.
    """
    try:
        import numpy as np

        arr = sorted(s)

        # The convolution output can be non-zero up to index 2*M_SIZE,
        # so we need an FFT buffer of at least that length.  Round up to
        # the next power of two for efficiency.
        n_fft = 1
        size = 2 * M_SIZE + 2
        while n_fft < size:
            n_fft <<= 1

        # Build the indicator vector: f[x] = 1 if x ∈ S, else 0.
        f = np.zeros(n_fft, dtype=np.float64)
        for x in arr:
            f[x] = 1.0

        # Compute the self-convolution g = f * f via FFT.
        # rfft/irfft exploit real symmetry and are faster than the full FFT.
        g = np.real(np.fft.irfft(np.fft.rfft(f) ** 2, n_fft))

        # For each b ∈ S, check whether any pair other than (b, b) sums to 2b.
        for b in arr:
            if g[2 * b] > 1.5:
                # FFT confirmed a 3-AP with middle element b; find and report it.
                _report_3ap(s, b)

    except ImportError:
        _check_no_3ap_pure(s)


def _report_3ap(s: set[int], b: int) -> None:
    """Find and report a 3-AP with middle element b."""
    for a in s:
        if a == b:
            continue
        c = 2 * b - a
        if c != a and c in s:
            raise ValueError(
                f"set contains a 3-term arithmetic progression: ({a}, {b}, {c})"
            )
    raise ValueError(f"set contains a 3-term arithmetic progression with middle element {b}")


def _check_no_3ap_pure(s: set[int]) -> None:
    """Pure-Python fallback for 3-AP detection. O(|S|^2).

    For every pair (a, b) with a < b, the only possible third element that
    would complete a 3-AP with middle b is c = 2b - a.  We check whether
    c ∈ S using the set for O(1) lookup.
    """
    arr = sorted(s)
    for i, a in enumerate(arr):
        for b in arr[i + 1:]:
            c = 2 * b - a
            if c in s:
                raise ValueError(
                    f"set contains a 3-term arithmetic progression: ({a}, {b}, {c})"
                )


def evaluate(solution_path: str) -> tuple[float, float, str]:
    raw_elements, _ = _run_solution(solution_path)
    elements = _to_elements(raw_elements)
    k = _validate_and_count(elements)

    if k <= BASELINE_SIZE:
        raw_score = 0.0
    else:
        raw_score = 100.0 * (k - BASELINE_SIZE) / k
    score = 100.0 * (raw_score / 100.0) ** SCORE_POWER
    score_unbounded = score
    message = (
        f"M={M_SIZE}; set_size={k}; baseline={BASELINE_SIZE}; "
        f"score_power={SCORE_POWER:.12g}; "
        f"raw_score={raw_score:.6f}; "
        f"score={score:.6f}; score_unbounded={score_unbounded:.6f}"
    )
    return score, score_unbounded, message


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: evaluator.py /path/to/solution.py", file=sys.stderr)
        return 1
    try:
        score, score_unbounded, message = evaluate(argv[1])
        print(message, file=sys.stderr)
        print(f"{score:.12f} {score_unbounded:.12f}")
        return 0
    except subprocess.TimeoutExpired:
        print(f"timed out after {TIMEOUT_SECONDS}s", file=sys.stderr)
        print("0.0 0.0")
        return 0
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        print("0.0 0.0")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

"""Evaluator for the Kissing Number 2.0 problem."""

from __future__ import annotations

import importlib.util
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

D = 9
# Best known upper bound for the d=9 kissing number (Odlyzko & Sloane, 1979).
UPPER_BOUND = 364
TIMEOUT_SECONDS = 10800
UNIT_TOL = 1e-6      # tolerance for |v| = 1
DOT_TOL = 1e-9       # tolerance for dot product ≤ 0.5
DISTINCT_TOL = 1e-6  # minimum L2 distance between distinct vectors


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


def _to_vectors(raw: Any) -> list[list[float]]:
    try:
        rows = raw.tolist()
    except Exception:
        rows = list(raw)

    vectors: list[list[float]] = []
    for index, row in enumerate(rows):
        try:
            vec = [float(x) for x in row]
        except Exception:
            raise ValueError(f"vector {index} cannot be converted to floats")
        vectors.append(vec)
    return vectors


def _run_solution(solution_path: str) -> tuple[Any, str]:
    with tempfile.TemporaryDirectory(prefix="kissing_number_") as tmp:
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
d = __D__


def load_vectors():
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in ("solve", "generate_vectors", "run"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn(d)

    vectors = getattr(module, "VECTORS", None)
    if vectors is not None:
        return vectors

    raise RuntimeError("solution must define solve(d), generate_vectors(d), run(d), or VECTORS")

try:
    vectors = load_vectors()
    with result_path.open("wb") as f:
        pickle.dump({"vectors": vectors}, f)
except Exception:
    with result_path.open("wb") as f:
        pickle.dump({"error": "solution failed while generating vectors"}, f)
""".replace("__SOLUTION_PATH__", repr(str(isolated_solution_path)))
            .replace("__RESULT_PATH__", repr(str(result_path)))
            .replace("__D__", repr(D)),
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
            raise RuntimeError("solution failed while generating vectors")
        return payload["vectors"], ""


def _validate_and_count(vectors: list[list[float]]) -> tuple[int, float]:
    """Validate the vector set; return (count, max_dot_product).

    Raises ValueError on any violation.

    The kissing number constraint is:
      - Each vector must be a unit vector: |v| = 1 ± UNIT_TOL.
      - All vectors must be distinct: pairwise L2 distance > DISTINCT_TOL.
      - Pairwise dot products must be ≤ 0.5 + DOT_TOL.

    Uses numpy for efficient O(K²) pairwise dot product computation.
    """
    import numpy as np

    if len(vectors) == 0:
        raise ValueError("solution returned an empty vector list")

    mat = np.array(vectors, dtype=np.float64)
    k, dim = mat.shape

    if dim != D:
        raise ValueError(f"expected dimension {D}, got {dim}")

    # Check unit norm
    norms = np.linalg.norm(mat, axis=1)
    bad = np.where(np.abs(norms - 1.0) > UNIT_TOL)[0]
    if len(bad) > 0:
        idx = int(bad[0])
        raise ValueError(
            f"vector {idx} is not a unit vector: |v| = {norms[idx]:.8f}"
        )

    # Check pairwise dot products and distinctness
    # G[i,j] = dot(v_i, v_j); diagonal = 1 (unit vectors)
    G = mat @ mat.T
    max_dot = float(np.max(G - 2.0 * np.eye(k)))  # ignore diagonal

    # Check distinctness via L2 distance: dist²(i,j) = 2 - 2*dot(i,j)
    # dist = 0 iff dot = 1; we require dist > DISTINCT_TOL ↔ dot < 1 - DISTINCT_TOL²/2
    dist_sq = 2.0 - 2.0 * G
    np.fill_diagonal(dist_sq, np.inf)
    min_dist_sq = float(np.min(dist_sq))
    if min_dist_sq < DISTINCT_TOL ** 2:
        i, j = np.unravel_index(int(np.argmin(dist_sq)), dist_sq.shape)
        raise ValueError(
            f"vectors {i} and {j} are not distinct: L2 distance = {min_dist_sq**0.5:.2e}"
        )

    if max_dot > 0.5 + DOT_TOL:
        # Find the offending pair
        off_diag = G.copy()
        np.fill_diagonal(off_diag, -np.inf)
        i, j = np.unravel_index(int(np.argmax(off_diag)), off_diag.shape)
        raise ValueError(
            f"dot product between vectors {i} and {j} is {G[i, j]:.8f} > 0.5"
        )

    return k, max_dot


def evaluate(solution_path: str) -> tuple[float, float, str]:
    raw_vectors, _ = _run_solution(solution_path)
    vectors = _to_vectors(raw_vectors)
    k, max_dot = _validate_and_count(vectors)

    score = 100.0 * k / UPPER_BOUND
    score_unbounded = score
    message = (
        f"d={D}; K={k}; upper_bound={UPPER_BOUND}; "
        f"max_dot={max_dot:.6f}; "
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

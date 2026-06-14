"""Evaluator for the Erdos Heilbronn triangle 2.0 problem."""

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

N_POINTS = 64
# Baseline area: a convenient threshold well below good constructions.
# Corresponds to N²·Δ = 0.25, which random point sets rarely exceed.
BASELINE_AREA = 1.0 / (4 * N_POINTS * N_POINTS)  # 1/16384 ≈ 6.1e-5
TIMEOUT_SECONDS = 10800
SCORE_POWER = 3.0
MIN_SEPARATION = 1e-9  # points must be distinct


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


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def _to_points(raw: Any) -> list[tuple[float, float]]:
    try:
        values = raw.tolist()
    except Exception:
        values = list(raw)

    points: list[tuple[float, float]] = []
    for index, item in enumerate(values):
        try:
            pair = item.tolist()
        except Exception:
            pair = item
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(f"point {index} is not a 2D coordinate pair")
        x, y = pair
        if not _is_number(x) or not _is_number(y):
            raise ValueError(f"point {index} has a non-finite coordinate")
        points.append((float(x), float(y)))
    return points


def _load_points(solution_path: str) -> Any:
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import solution from {solution_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in ("solve", "generate_points", "run"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn(N_POINTS)

    points = getattr(module, "POINTS", None)
    if points is not None:
        return points

    raise RuntimeError("solution must define solve(n), generate_points(n), run(n), or POINTS")


def _run_solution(solution_path: str) -> tuple[Any, str]:
    with tempfile.TemporaryDirectory(prefix="erdos_heilbronn_") as tmp:
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
n_points = __N_POINTS__


def load_points():
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in ("solve", "generate_points", "run"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn(n_points)

    points = getattr(module, "POINTS", None)
    if points is not None:
        return points

    raise RuntimeError("solution must define solve(n), generate_points(n), run(n), or POINTS")

try:
    points = load_points()
    with result_path.open("wb") as f:
        pickle.dump({"points": points}, f)
except Exception:
    with result_path.open("wb") as f:
        pickle.dump({"error": "solution failed while generating points"}, f)
""".replace("__SOLUTION_PATH__", repr(str(isolated_solution_path)))
            .replace("__RESULT_PATH__", repr(str(result_path)))
            .replace("__N_POINTS__", repr(N_POINTS)),
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
            raise RuntimeError("solution failed while generating points")
        return payload["points"], ""


def _validate_points(points: list[tuple[float, float]]) -> None:
    if len(points) != N_POINTS:
        raise ValueError(f"expected {N_POINTS} points, got {len(points)}")

    min_sep2 = MIN_SEPARATION * MIN_SEPARATION
    for index, (x, y) in enumerate(points):
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"point {index} has a non-finite coordinate")
        if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
            raise ValueError(f"point {index} = ({x}, {y}) is outside [0, 1]²")

    # Check all pairs for duplicates using a spatial bucket
    buckets: dict[tuple[int, int], list[tuple[float, float]]] = {}
    cell = MIN_SEPARATION
    for index, (x, y) in enumerate(points):
        key = (int(x / cell), int(y / cell))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for px, py in buckets.get((key[0] + dx, key[1] + dy), ()):
                    if (x - px) * (x - px) + (y - py) * (y - py) < min_sep2:
                        raise ValueError(
                            f"points {index} and another point are identical "
                            f"(distance < {MIN_SEPARATION:g})"
                        )
        buckets.setdefault(key, []).append((x, y))


def _min_triangle_area(points: list[tuple[float, float]]) -> float:
    """Compute the minimum triangle area over all C(N,3) triples.

    Uses numpy to vectorize the innermost loop. For each fixed pair (i, j),
    the cross product with all remaining points k > j is computed in one
    batch, giving O(N²) numpy calls each processing O(N) elements.

    Area of triangle (p_i, p_j, p_k):
        area = 0.5 * |( p_j - p_i ) × ( p_k - p_i )|
             = 0.5 * |(dx1 * dy2 - dy1 * dx2)|
    where dx1,dy1 = p_j - p_i and dx2,dy2 = p_k - p_i.
    """
    try:
        import numpy as np

        pts = np.array(points, dtype=np.float64)
        n = len(pts)
        min_area = np.inf
        for i in range(n):
            for j in range(i + 1, n):
                dx1 = pts[j, 0] - pts[i, 0]
                dy1 = pts[j, 1] - pts[i, 1]
                # Vectorise over all k > j at once
                dx2 = pts[j + 1:, 0] - pts[i, 0]
                dy2 = pts[j + 1:, 1] - pts[i, 1]
                if dx2.size == 0:
                    continue
                areas = 0.5 * np.abs(dx1 * dy2 - dy1 * dx2)
                m = float(areas.min())
                if m < min_area:
                    min_area = m
        return min_area

    except ImportError:
        return _min_triangle_area_pure(points)


def _min_triangle_area_pure(points: list[tuple[float, float]]) -> float:
    """Pure-Python fallback. O(N³)."""
    n = len(points)
    min_area = float("inf")
    for i in range(n):
        xi, yi = points[i]
        for j in range(i + 1, n):
            dx1 = points[j][0] - xi
            dy1 = points[j][1] - yi
            for k in range(j + 1, n):
                dx2 = points[k][0] - xi
                dy2 = points[k][1] - yi
                area = 0.5 * abs(dx1 * dy2 - dy1 * dx2)
                if area < min_area:
                    min_area = area
    return min_area


def evaluate(solution_path: str) -> tuple[float, float, str]:
    raw_points, _ = _run_solution(solution_path)
    points = _to_points(raw_points)
    _validate_points(points)
    delta = _min_triangle_area(points)

    if delta <= BASELINE_AREA:
        raw_score = 0.0
    else:
        raw_score = 100.0 * (1.0 - BASELINE_AREA / delta)
    score = 100.0 * (raw_score / 100.0) ** SCORE_POWER
    score_unbounded = score
    message = (
        f"N={N_POINTS}; min_triangle_area={delta:.9f}; "
        f"N2_delta={N_POINTS * N_POINTS * delta:.6f}; "
        f"baseline={BASELINE_AREA:.9f}; score_power={SCORE_POWER:.12g}; "
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

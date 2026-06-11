"""Baseline solution: hexagonal lattice in the z=0 plane.

Each interior point has 6 unit-distance neighbors, giving roughly 3*N unit
pairs for a square patch — well above the N-pair baseline required for a
non-zero score.
"""

from __future__ import annotations

import math


def solve(n: int) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    side = int(math.ceil(math.sqrt(n))) + 2
    for row in range(side * 2):
        for col in range(side * 2):
            if len(points) >= n:
                return points[:n]
            x = col + 0.5 * (row % 2)
            y = row * (math.sqrt(3) / 2)
            points.append((x, y, 0.0))
    return points[:n]

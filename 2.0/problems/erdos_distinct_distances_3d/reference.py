"""Reference solution: cbrt(N) x cbrt(N) x cbrt(N) integer cube.

The cubic integer lattice is the best known construction for the 3D Erdős
distinct distances problem.  By Legendre's three-square theorem, only integers
of the form 4^a(8b+7) are NOT representable as a sum of three squares, roughly
1/6 of all integers.  This means a k×k×k grid achieves about 5/6 × 3(k-1)²
≈ O(N^{2/3}) distinct distances — far fewer than the planar square lattice.

For N = 4096 (k = 16) this lattice achieves 401 distinct distances,
giving a score of about 90.2.
"""

import math


def solve(n: int) -> list[tuple[float, float, float]]:
    side = round(n ** (1 / 3))
    if side ** 3 != n:
        raise ValueError(f"reference solution requires n to be a perfect cube, got {n}")
    return [
        (float(i), float(j), float(k))
        for i in range(side)
        for j in range(side)
        for k in range(side)
    ]

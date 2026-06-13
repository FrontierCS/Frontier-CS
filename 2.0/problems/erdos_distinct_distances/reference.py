"""Reference solution: sqrt(N) x sqrt(N) integer lattice.

The square integer lattice is the best known construction for the Erdős
distinct distances problem.  By the Landau–Ramanujan theorem, the number of
integers up to x representable as a sum of two squares grows as Θ(x / √log x),
so a k×k grid has Θ(k² / √log k) = Θ(N / √log N) distinct distances.

For N = 4096 (k = 64) this lattice achieves 1575 distinct distances,
giving a score of about 61.5.
"""

import math


def solve(n: int) -> list[tuple[float, float]]:
    side = math.isqrt(n)
    if side * side != n:
        raise ValueError(f"reference solution requires n to be a perfect square, got {n}")
    return [(float(i), float(j)) for i in range(side) for j in range(side)]

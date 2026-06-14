"""Reference solution for the Erdos Heilbronn problem.

Uses a vectorized greedy construction: points are added one at a time,
each time choosing the candidate (from a random pool) that maximises the
minimum triangle area with all already-placed points.

Expected: min_triangle_area ≈ 3.3e-4, N²·Δ ≈ 1.36, score ≈ 54.
"""

import numpy as np


def solve(n: int) -> list[tuple[float, float]]:
    rng = np.random.default_rng(0)

    # Start with 2 random seed points
    pts = list(rng.random((2, 2)))

    n_candidates = 1000

    for _ in range(n - 2):
        k = len(pts)
        ppts = np.array(pts, dtype=np.float64)  # (k, 2)

        # Pre-compute difference vectors for all existing pairs (i, j)
        ii, jj = np.triu_indices(k, k=1)
        dx1 = ppts[jj, 0] - ppts[ii, 0]  # (n_pairs,)
        dy1 = ppts[jj, 1] - ppts[ii, 1]

        # Sample candidate points uniformly from [0, 1]²
        cands = rng.random((n_candidates, 2))  # (n_candidates, 2)

        # For each candidate, compute its minimum triangle area with all
        # existing pairs.  Broadcasting: (n_candidates, n_pairs).
        dx2 = cands[:, 0:1] - ppts[ii, 0]  # (n_candidates, n_pairs)
        dy2 = cands[:, 1:2] - ppts[ii, 1]
        cross = dx1 * dy2 - dy1 * dx2
        areas = 0.5 * np.abs(cross)
        min_areas = areas.min(axis=1)  # (n_candidates,)

        # Keep the candidate with the largest minimum-triangle-area guarantee
        best = int(np.argmax(min_areas))
        pts.append(cands[best])

    return [(float(p[0]), float(p[1])) for p in pts]

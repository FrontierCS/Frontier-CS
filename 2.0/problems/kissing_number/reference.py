"""Reference solution for the Kissing Number problem in d=9.

Two-phase construction combining the D9 lattice shell with greedy signed-unit
vectors.

Phase 1 — D9 shell: all (±e_i ± e_j)/√2 for i < j.
  - 4 * C(9,2) = 144 vectors.
  - Any two such vectors have dot product in {-1, -1/2, 0, 1/2, 1}; the ±1
    cases are opposite/equal vectors (excluded). All 144 are mutually valid.

Phase 2 — Signed-unit vectors (±1/√d, …, ±1/√d):
  - |v|² = d * (1/√d)² = 1. ✓
  - Dot with a D9 shell vector: ≤ √(2/d) = √(2/9) ≈ 0.471 ≤ 0.5. ✓
  - Pairwise dot: (agreements − disagreements)/d ≤ 1/2.
  - Greedy selection collects 32 compatible signed-unit vectors.

Total: 144 + 32 = 176. Expected: K=176, score≈48.4.

The best known construction reaches K=306; improving over 176 is the challenge.
"""

from __future__ import annotations

import math


def solve(d: int) -> list[list[float]]:
    """Build the D9⁺ kissing configuration for d=9.

    Two-phase construction:
      Phase 1 — D9 shell (type ±e_i ± e_j):
        Each vector has exactly two nonzero entries (±1/√2).
        Any two such vectors have dot product 0, ±1/2, or ±1.
        Dot = ±1 only when the vectors are equal or opposite (excluded).
        All 144 are mutually valid.

      Phase 2 — Signed-unit vectors (±1/√d, …, ±1/√d):
        |v|² = d * (1/√d)² = 1. ✓
        Dot with a D9 vector (±e_i ± e_j)/√2 is (±v_i ± v_j)/√2
        = ±2/(√d · √2) = ±√(2/d).
        For d=9: √(2/9) ≈ 0.471 ≤ 0.5. ✓
        Dot between two signed-unit vectors u, v:
        = (agreements − disagreements)/d.
        Must have agreements − disagreements ≤ d/2.
        We greedily add signed-unit vectors satisfying this.
    """
    assert d == 9, f"this reference is designed for d=9, got d={d}"

    inv_sqrt2 = 1.0 / math.sqrt(2)
    vectors: list[list[float]] = []

    # Phase 1: D9 shell — all (±e_i ± e_j)/sqrt(2) for i < j
    for i in range(d):
        for j in range(i + 1, d):
            for si in (1.0, -1.0):
                for sj in (1.0, -1.0):
                    v = [0.0] * d
                    v[i] = si * inv_sqrt2
                    v[j] = sj * inv_sqrt2
                    vectors.append(v)

    # Phase 2: greedily add signed-unit vectors (±1/√d, …, ±1/√d).
    # Each such vector has |v|² = d * (1/√d)² = 1. ✓
    # Pairwise dot between two such vectors u, v:
    #   dot(u, v) = (agreements − disagreements) / d
    # where agreements + disagreements = d.  For dot ≤ 1/2 we need
    #   agreements ≤ (d + d/2) / 2 = 3d/4, i.e. ≤ 6 agreements for d=9.
    # Dot with a D9 shell vector (±e_i ± e_j)/√2:
    #   = (±v_i ± v_j)/√2 ≤ 2 / (√d · √2) = √(2/d) ≈ 0.471 ≤ 0.5 for d=9. ✓
    inv_sqrtd = 1.0 / math.sqrt(d)
    candidates: list[list[float]] = []
    for mask in range(1 << d):
        v = [inv_sqrtd if not (mask >> k & 1) else -inv_sqrtd for k in range(d)]
        candidates.append(v)

    # For each candidate, check dot product ≤ 0.5 with all accepted vectors.
    for cand in candidates:
        valid = True
        for existing in vectors:
            dot = sum(cand[k] * existing[k] for k in range(d))
            if dot > 0.5 + 1e-9:
                valid = False
                break
        if valid:
            vectors.append(cand)

    return vectors

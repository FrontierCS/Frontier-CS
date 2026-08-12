"""MetaOpt clustered-V2 baseline retained for calibration."""
from __future__ import annotations

import hashlib
import itertools
import random
from typing import Any, Callable


def search(instance: dict[str, Any], evaluate_gap: Callable[[Any], tuple[float, ...]]) -> list[int]:
    """Optimize each disclosed cluster block exactly, then fix it permanently."""
    current = None
    current_gap = -1.0
    for trial in range(10):
        seed = int.from_bytes(
            hashlib.sha256(
                (f"paper-init:{trial}:" + instance["id"]).encode("ascii")
            ).digest()[:8],
            "big",
        )
        rng = random.Random(seed)
        candidate = [0] * len(instance["pairs"])
        for pair_index in rng.sample(range(len(candidate)), instance["density_limit"]):
            candidate[pair_index] = rng.randrange(1, len(instance["levels"]))
        try:
            gap = evaluate_gap(candidate)[0]
        except ValueError:
            continue
        if gap > current_gap:
            current_gap = gap
            current = candidate
    if current is None:
        current = [0] * len(instance["pairs"])
    for block in instance["search_blocks"]:
        best: list[int] | None = None
        best_gap = -1.0
        for values in itertools.product(range(len(instance["levels"])), repeat=len(block)):
            candidate = current.copy()
            for pair_index, value in zip(block, values):
                candidate[pair_index] = value
            try:
                gap = evaluate_gap(candidate)[0]
            except ValueError:
                continue
            if gap > best_gap + 1e-9 or (
                abs(gap - best_gap) <= 1e-9 and (best is None or tuple(candidate) < tuple(best))
            ):
                best_gap = gap
                best = candidate
        if best is None:
            raise RuntimeError("no feasible block assignment")
        current = best
    return current

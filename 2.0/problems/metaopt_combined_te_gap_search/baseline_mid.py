"""Mid-effort deterministic random sampling under the replay budget."""
from __future__ import annotations

import hashlib
import random


def search(instance, evaluate_gap):
    seed = int.from_bytes(hashlib.sha256(instance["id"].encode("ascii")).digest()[:8], "big")
    rng = random.Random(seed)
    best = [0] * len(instance["pairs"])
    best_gap = -1.0
    for _ in range(instance["query_budget"]):
        answer = [0] * len(instance["pairs"])
        count = rng.randint(max(1, instance["density_limit"] // 2), instance["density_limit"])
        for index in rng.sample(range(len(answer)), count):
            answer[index] = rng.randrange(1, len(instance["levels"]))
        try:
            gap = evaluate_gap(answer)[0]
        except ValueError:
            continue
        if gap > best_gap:
            best_gap = gap
            best = answer
    return best

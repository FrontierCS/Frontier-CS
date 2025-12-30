import pandas as pd
import numpy as np
from itertools import permutations


class Solution:
    def __init__(self):
        self._hash_base = 911382323
        self._hash_mask = (1 << 64) - 1

    def _apply_col_merge(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df2 = df.copy()
        orig_cols = list(df.columns)

        for group in col_merge:
            if group is None:
                continue
            if not isinstance(group, (list, tuple)):
                group = [group]
            if len(group) < 2:
                continue

            cols = []
            for g in group:
                if isinstance(g, (int, np.integer)):
                    if 0 <= int(g) < len(orig_cols):
                        name = orig_cols[int(g)]
                    else:
                        continue
                else:
                    name = str(g)
                if name in df2.columns and name not in cols:
                    cols.append(name)

            if len(cols) < 2:
                continue

            try:
                positions = [df2.columns.get_loc(c) for c in cols]
                loc = min(positions)
            except Exception:
                loc = 0

            merged = df2[cols[0]].astype(str)
            for c in cols[1:]:
                merged = merged + df2[c].astype(str)

            base_name = "_".join(cols)
            new_name = base_name
            if new_name in df2.columns and new_name not in cols:
                k = 2
                while f"{base_name}_{k}" in df2.columns:
                    k += 1
                new_name = f"{base_name}_{k}"

            df2.drop(columns=cols, inplace=True)
            if loc > len(df2.columns):
                loc = len(df2.columns)
            df2.insert(loc=loc, column=new_name, value=merged)

        return df2

    def _score_perm_hash(self, col_lists, perm, n_rows, max_chars):
        base = self._hash_base
        mask = self._hash_mask
        prefix_sets = [set() for _ in range(max_chars + 1)]

        total = 0
        first = True

        for idx in range(n_rows):
            h = 0
            depth = 0
            best = 0

            for pi in perm:
                s = col_lists[pi][idx]
                for ch in s:
                    depth += 1
                    if depth > max_chars:
                        break
                    h = (h * base + (ord(ch) + 1)) & mask
                    ps = prefix_sets[depth]
                    if h in ps:
                        best = depth
                    ps.add(h)
                if depth >= max_chars:
                    break

            if first:
                first = False
            else:
                total += best

        return total

    def solve(
        self,
        df: pd.DataFrame,
        early_stop: int = 100000,
        row_stop: int = 4,
        col_stop: int = 2,
        col_merge: list = None,
        one_way_dep: list = None,
        distinct_value_threshold: float = 0.7,
        parallel: bool = True,
    ) -> pd.DataFrame:
        df2 = self._apply_col_merge(df, col_merge)
        cols = list(df2.columns)
        m = len(cols)
        if m <= 1:
            return df2

        n = len(df2)
        if n == 0:
            return df2

        sample_n = min(n, max(800, int(row_stop) * 1000))
        max_chars = 96

        col_lists = []
        distinct_ratios = []
        avg_lens = []
        first1_ratios = []
        first2_ratios = []

        for c in cols:
            arr = df2[c].astype(str).tolist()
            col_lists.append(arr)

            d = len(set(arr)) / n
            distinct_ratios.append(d)

            total_len = 0
            f1 = set()
            f2 = set()
            for s in arr[:sample_n]:
                total_len += len(s)
                if s:
                    f1.add(s[0])
                    f2.add(s[:2] if len(s) >= 2 else s)
                else:
                    f1.add("")
                    f2.add("")
            avg_lens.append(total_len / sample_n if sample_n else 0.0)
            first1_ratios.append(len(f1) / sample_n if sample_n else 1.0)
            first2_ratios.append(len(f2) / sample_n if sample_n else 1.0)

        def add_perm(p, perms, seen):
            t = tuple(p)
            if t not in seen:
                perms.append(p)
                seen.add(t)

        perms = []
        seen = set()
        base_perm = list(range(m))
        add_perm(base_perm, perms, seen)
        add_perm(list(reversed(base_perm)), perms, seen)

        add_perm(sorted(range(m), key=lambda i: (distinct_ratios[i], -avg_lens[i])), perms, seen)
        add_perm(sorted(range(m), key=lambda i: (-avg_lens[i], distinct_ratios[i])), perms, seen)
        add_perm(sorted(range(m), key=lambda i: (distinct_ratios[i] / (avg_lens[i] + 1e-6), distinct_ratios[i], -avg_lens[i])), perms, seen)
        add_perm(sorted(range(m), key=lambda i: (-(avg_lens[i] * (1.0 - distinct_ratios[i])), distinct_ratios[i], -avg_lens[i])), perms, seen)
        add_perm(sorted(range(m), key=lambda i: (first2_ratios[i], distinct_ratios[i], -avg_lens[i])), perms, seen)
        add_perm(sorted(range(m), key=lambda i: (first1_ratios[i], distinct_ratios[i], -avg_lens[i])), perms, seen)

        low = [i for i in range(m) if distinct_ratios[i] <= distinct_value_threshold]
        high = [i for i in range(m) if distinct_ratios[i] > distinct_value_threshold]
        low_sorted = sorted(low, key=lambda i: (distinct_ratios[i], -avg_lens[i]))
        high_sorted = sorted(high, key=lambda i: (distinct_ratios[i], -avg_lens[i]))
        add_perm(low_sorted + high_sorted, perms, seen)

        score_cache = {}

        def get_score(p):
            tp = tuple(p)
            sc = score_cache.get(tp)
            if sc is not None:
                return sc
            sc = self._score_perm_hash(col_lists, p, sample_n, max_chars)
            score_cache[tp] = sc
            return sc

        best_p = perms[0]
        best_score = -1
        evals = 0
        for p in perms:
            if evals >= early_stop:
                break
            sc = get_score(p)
            evals += 1
            if sc > best_score:
                best_score = sc
                best_p = p

        max_iters = min(6, max(1, int(col_stop) * 2))
        for _ in range(max_iters):
            if evals >= early_stop:
                break
            current = best_p
            current_score = best_score
            improved = False

            best_neighbor = current
            best_neighbor_score = current_score

            for i in range(m - 1):
                if evals >= early_stop:
                    break
                for j in range(i + 1, m):
                    if evals >= early_stop:
                        break
                    nb = current.copy()
                    nb[i], nb[j] = nb[j], nb[i]
                    sc = get_score(nb)
                    evals += 1
                    if sc > best_neighbor_score:
                        best_neighbor_score = sc
                        best_neighbor = nb
                        improved = True

            if improved and best_neighbor_score > best_score:
                best_p = best_neighbor
                best_score = best_neighbor_score
            else:
                break

        ordered_cols = [cols[i] for i in best_p]
        return df2[ordered_cols]
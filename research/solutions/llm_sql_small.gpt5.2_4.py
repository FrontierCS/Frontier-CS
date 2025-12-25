import numpy as np
import pandas as pd


_MASK64 = (1 << 64) - 1
_FNV_OFFSET = 1469598103934665603
_FNV_PRIME = 1099511628211


def _ensure_unique_name(cols, base):
    if base not in cols:
        return base
    k = 1
    while True:
        name = f"{base}__m{k}"
        if name not in cols:
            return name
        k += 1


def _apply_col_merge(df: pd.DataFrame, col_merge):
    if not col_merge:
        return df
    df_work = df.copy()
    orig_cols = list(df_work.columns)

    for group in col_merge:
        if not group:
            continue
        # Interpret group as names or indices
        names = None
        if all(isinstance(x, (int, np.integer)) for x in group):
            names = []
            for idx in group:
                idx = int(idx)
                if 0 <= idx < len(orig_cols):
                    names.append(orig_cols[idx])
        else:
            names = [str(x) for x in group]

        present = [c for c in names if c in df_work.columns]
        if len(present) <= 1:
            continue

        first_pos = df_work.columns.get_loc(present[0])
        merged = df_work[present[0]].astype(str)
        for c in present[1:]:
            merged = merged + df_work[c].astype(str)

        new_name_base = "+".join(present)
        new_name = _ensure_unique_name(set(df_work.columns), new_name_base)

        cols = list(df_work.columns)
        for c in present:
            if c in cols:
                cols.remove(c)
        cols.insert(first_pos, new_name)

        df_work[new_name] = merged
        df_work = df_work[cols]

    return df_work


def _exact_score_boundary(order, code_cols, len_cols, n_rows):
    m = len(order)
    if m <= 0 or n_rows <= 1:
        return 0
    sets = [set() for _ in range(m)]
    hashes = [0] * m
    num = 0
    offset = _FNV_OFFSET
    prime = _FNV_PRIME
    mask = _MASK64
    for i in range(n_rows):
        h = offset
        cum = 0
        best = 0
        for t in range(m):
            cidx = order[t]
            h = ((h ^ (int(code_cols[cidx][i]) + 1)) * prime) & mask
            cum += int(len_cols[cidx][i])
            hashes[t] = h
            if i and (h in sets[t]):
                best = cum
        if i:
            num += best
        for t in range(m):
            sets[t].add(hashes[t])
    return num


class Solution:
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
        df_work = _apply_col_merge(df, col_merge)
        cols = list(df_work.columns)
        m = len(cols)
        if m <= 1:
            return df_work.astype(str)

        sdf = df_work.astype(str)
        n = len(sdf)
        if n <= 1:
            return sdf

        codes = np.empty((n, m), dtype=np.int32)
        lens = np.empty((n, m), dtype=np.int32)
        for j, c in enumerate(cols):
            arr = sdf[c].to_numpy()
            codes[:, j] = pd.factorize(arr, sort=False)[0].astype(np.int32, copy=False)
            lens[:, j] = sdf[c].str.len().to_numpy(dtype=np.int32, copy=False)

        codes1 = [codes[:, j].astype(np.uint64, copy=False) + np.uint64(1) for j in range(m)]
        len_cols_np = [lens[:, j].astype(np.int32, copy=False) for j in range(m)]

        # Greedy construction using fast frequency-based approximation
        remaining = list(range(m))
        order = []
        prefkey = np.full(n, np.uint64(_FNV_OFFSET), dtype=np.uint64)
        cumlen = np.zeros(n, dtype=np.int32)
        prime_u = np.uint64(_FNV_PRIME)

        for _pos in range(m):
            best_c = None
            best_score = -1

            for c in remaining:
                newkey = (prefkey ^ codes1[c]) * prime_u
                uniq, idx, cnt = np.unique(newkey, return_index=True, return_counts=True)
                if cnt.size == 0:
                    score = 0
                else:
                    cum = cumlen[idx].astype(np.int64) + len_cols_np[c][idx].astype(np.int64)
                    score = int(np.sum((cnt.astype(np.int64) - 1) * cum))
                if score > best_score:
                    best_score = score
                    best_c = c

            order.append(best_c)
            remaining.remove(best_c)
            prefkey = (prefkey ^ codes1[best_c]) * prime_u
            cumlen += len_cols_np[best_c]

        # Local improvement using exact boundary sequential score
        code_cols = [codes[:, j] for j in range(m)]
        len_cols = [lens[:, j] for j in range(m)]

        best_exact = _exact_score_boundary(order, code_cols, len_cols, n)
        max_iters = int(col_stop) if isinstance(col_stop, (int, np.integer)) else 2
        if max_iters <= 0:
            max_iters = 1

        eval_budget = int(early_stop) if isinstance(early_stop, (int, np.integer)) else 100000
        eval_count = 0

        for _it in range(max_iters):
            improved = False
            # try all swaps, take best improvement
            best_swap = None
            best_swap_score = best_exact
            for i in range(m - 1):
                for j in range(i + 1, m):
                    if eval_count >= eval_budget:
                        break
                    cand = order.copy()
                    cand[i], cand[j] = cand[j], cand[i]
                    sc = _exact_score_boundary(cand, code_cols, len_cols, n)
                    eval_count += 1
                    if sc > best_swap_score:
                        best_swap_score = sc
                        best_swap = (i, j)
                if eval_count >= eval_budget:
                    break
            if best_swap is not None:
                i, j = best_swap
                order[i], order[j] = order[j], order[i]
                best_exact = best_swap_score
                improved = True
            if not improved or eval_count >= eval_budget:
                break

        out_cols = [cols[i] for i in order]
        return df_work[out_cols].astype(str)
import numpy as np
import pandas as pd
from typing import List, Any, Dict, Tuple, Optional


def _lcp_len(a: str, b: str) -> int:
    la = len(a)
    lb = len(b)
    n = la if la < lb else lb
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _make_unique_name(existing: set, base: str) -> str:
    if base not in existing:
        existing.add(base)
        return base
    k = 2
    while True:
        name = f"{base}__{k}"
        if name not in existing:
            existing.add(name)
            return name
        k += 1


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
        if df is None or df.shape[1] <= 1:
            return df

        if col_merge:
            df = df.copy()
            existing_names = set(df.columns)
            for grp in col_merge:
                if not grp or len(grp) < 2:
                    continue
                cols = []
                for x in grp:
                    if isinstance(x, (int, np.integer)):
                        ix = int(x)
                        if 0 <= ix < len(df.columns):
                            cols.append(df.columns[ix])
                    else:
                        cols.append(x)
                cols = [c for c in cols if c in df.columns]
                if len(cols) < 2:
                    continue
                insert_pos = min(int(df.columns.get_loc(c)) for c in cols)
                s = df[cols[0]].astype(str)
                for c in cols[1:]:
                    s = s + df[c].astype(str)
                base_name = "+".join(cols)
                new_name = _make_unique_name(existing_names, base_name)
                df = df.drop(columns=cols)
                df.insert(insert_pos, new_name, s)

        cols_all = list(df.columns)
        m = len(cols_all)
        if m <= 1:
            return df

        n = len(df)
        if n <= 1:
            return df

        n_sample = min(n, 8000)
        if n_sample < n:
            rng = np.random.default_rng(0)
            sample_idx = rng.choice(n, size=n_sample, replace=False)
        else:
            sample_idx = np.arange(n, dtype=np.int64)

        # Precompute per-column sample strings and hashes
        col_hash: Dict[Any, np.ndarray] = {}
        stats: Dict[Any, Dict[str, float]] = {}
        avg_lens = []

        for c in cols_all:
            sarr = df[c].iloc[sample_idx].astype(str).to_numpy(dtype=object, copy=False)
            uniq, counts = np.unique(sarr, return_counts=True)
            u = int(len(uniq))
            distinct_ratio = u / float(n_sample)
            freq_max = float(counts.max()) / float(n_sample) if u > 0 else 0.0

            lens = np.fromiter((len(x) for x in sarr), dtype=np.int32, count=n_sample)
            avg_len = float(lens.mean()) if n_sample > 0 else 0.0
            avg_lens.append(avg_len)

            prefix_mode_avg = 0.0
            common_all = 0.0
            mode_len = 0.0
            if u > 0:
                mode_i = int(np.argmax(counts))
                mode = str(uniq[mode_i])
                mode_len = float(len(mode))
                # Common prefix across all values (since uniq is sorted lexicographically)
                common_all = float(_lcp_len(str(uniq[0]), str(uniq[-1]))) if u >= 2 else float(len(mode))
                # Average LCP to mode among top frequent values
                topk = min(u, 80)
                if topk > 1:
                    top_idx = np.argpartition(-counts, topk - 1)[:topk]
                    total = 0.0
                    for idx in top_idx:
                        val = str(uniq[int(idx)])
                        lcp = _lcp_len(mode, val)
                        total += float(counts[int(idx)]) * float(lcp)
                    prefix_mode_avg = total / float(n_sample)

            prefix_score = max(prefix_mode_avg, common_all)
            stats[c] = {
                "distinct_ratio": float(distinct_ratio),
                "freq_max": float(freq_max),
                "avg_len": float(avg_len),
                "prefix_score": float(prefix_score),
                "mode_len": float(mode_len),
            }

            try:
                col_hash[c] = pd.util.hash_array(sarr, categorize=True).astype(np.uint64, copy=False)
            except Exception:
                # Fallback: use pandas hashing on a Series
                col_hash[c] = pd.util.hash_pandas_object(pd.Series(sarr), index=False).to_numpy(dtype=np.uint64, copy=False)

        global_avg_len = float(np.mean(avg_lens)) if avg_lens else 1.0
        if global_avg_len <= 0:
            global_avg_len = 1.0

        def base_key(cname: Any) -> Tuple[int, float, float, float, float, str]:
            st = stats[cname]
            dr = st["distinct_ratio"]
            bucket = 0 if dr <= float(distinct_value_threshold) else 1
            return (
                bucket,
                dr,
                -st["freq_max"],
                -st["prefix_score"],
                -st["avg_len"],
                str(cname),
            )

        base_order = sorted(cols_all, key=base_key)

        # Greedy selection for early columns using conditional duplicate strength
        k_greedy = min(12, m)
        pool_size = min(30, m)

        selected: List[Any] = []
        remaining = set(cols_all)

        key_hash = np.zeros(n_sample, dtype=np.uint64)
        MULT = np.uint64(1315423911)
        MIX = np.uint64(11400714819323198485)

        for step in range(k_greedy):
            cand = [c for c in base_order if c in remaining][:pool_size]
            if not cand:
                break

            if step == 0:
                pick = cand[0]
            else:
                group_id = pd.factorize(key_hash, sort=False)[0].astype(np.int32, copy=False)
                group_sizes = np.bincount(group_id)
                total_pairs = int(np.sum(group_sizes.astype(np.int64) * (group_sizes.astype(np.int64) - 1)))
                if total_pairs <= 0:
                    break

                best_score = -1e300
                pick = cand[0]
                for c in cand:
                    vh = col_hash[c]
                    key2 = vh ^ (group_id.astype(np.uint64, copy=False) * MIX)
                    _, counts = np.unique(key2, return_counts=True)
                    cnt = counts.astype(np.int64, copy=False)
                    sum_pairs = int(np.sum(cnt * (cnt - 1)))
                    pair_prob = float(sum_pairs) / float(total_pairs) if total_pairs > 0 else 0.0

                    st = stats[c]
                    dr = st["distinct_ratio"]
                    avg_len = st["avg_len"]
                    pref = st["prefix_score"]

                    score = (pair_prob * 3.0 + (1.0 - dr) * 0.8) * (avg_len + 0.5)
                    score += (pref / (avg_len + 1e-9)) * (avg_len + 0.5) * 0.15
                    score += (avg_len / global_avg_len) * 0.05

                    if score > best_score:
                        best_score = score
                        pick = c

            selected.append(pick)
            remaining.remove(pick)
            key_hash = (key_hash * MULT) ^ col_hash[pick]

        remaining_cols = [c for c in base_order if c in remaining]
        final_order = selected + remaining_cols

        if final_order == cols_all:
            return df
        return df.loc[:, final_order]
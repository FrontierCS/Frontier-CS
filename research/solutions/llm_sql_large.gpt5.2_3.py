import os
import math
import numpy as np
import pandas as pd


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df = df.copy()
        cols_all = list(df.columns)

        for group in col_merge:
            if not group:
                continue

            cols = []
            for x in group:
                if isinstance(x, (int, np.integer)):
                    if 0 <= int(x) < len(cols_all):
                        c = cols_all[int(x)]
                        if c in df.columns:
                            cols.append(c)
                else:
                    c = str(x)
                    if c in df.columns:
                        cols.append(c)

            # de-dup preserve order
            seen = set()
            cols2 = []
            for c in cols:
                if c not in seen and c in df.columns:
                    seen.add(c)
                    cols2.append(c)
            cols = cols2

            if len(cols) <= 1:
                continue

            base_name = "+".join(cols)
            new_name = base_name
            if new_name in df.columns:
                k = 1
                while True:
                    cand = f"{base_name}__m{k}"
                    if cand not in df.columns:
                        new_name = cand
                        break
                    k += 1

            merged = df[cols[0]].fillna("").astype(str)
            for c in cols[1:]:
                merged = merged + df[c].fillna("").astype(str)

            df = df.drop(columns=cols)
            df[new_name] = merged

        return df

    def _col_stats(self, s: pd.Series, k_pref: int = 3):
        arr = s.to_numpy(dtype=object, copy=False)
        n = arr.shape[0]
        if n == 0:
            return {
                "distinct_ratio": 1.0,
                "avg_len": 0.0,
                "collision": 0.0,
                "p1": 0.0,
                "p2": 0.0,
                "p3": 0.0,
                "elcp": 0.0,
                "strength": 0.0,
            }

        lengths = np.fromiter((len(x) for x in arr), dtype=np.int32, count=n)
        avg_len = float(lengths.mean()) if n else 0.0

        codes, uniques = pd.factorize(arr, sort=False)
        counts = np.bincount(codes, minlength=len(uniques)).astype(np.int64)
        n2 = float(n) * float(n)
        sumsq = float(np.dot(counts, counts))
        collision = sumsq / n2 if n2 else 0.0
        distinct_ratio = float(len(uniques)) / float(n) if n else 1.0

        weights = (counts.astype(np.float64) ** 2)
        den = float(weights.sum())
        if den > 0.0:
            lens_uniques = np.fromiter((len(u) for u in uniques), dtype=np.float64, count=len(uniques))
            elen_match = float(np.dot(weights, lens_uniques) / den)
        else:
            elen_match = 0.0

        p_list = []
        for t in range(1, k_pref + 1):
            pref = s.str.slice(0, t).to_numpy(dtype=object, copy=False)
            c2, u2 = pd.factorize(pref, sort=False)
            cnt2 = np.bincount(c2, minlength=len(u2)).astype(np.int64)
            p_t = float(np.dot(cnt2, cnt2)) / n2 if n2 else 0.0
            p_list.append(p_t)

        p1 = p_list[0] if len(p_list) >= 1 else 0.0
        p2 = p_list[1] if len(p_list) >= 2 else 0.0
        p3 = p_list[2] if len(p_list) >= 3 else 0.0

        elcp = p1 + p2 + p3
        if collision > 0.0 and elen_match > k_pref:
            elcp += collision * (elen_match - float(k_pref))

        strength = elcp + 2.0 * p1 + 0.25 * (1.0 - distinct_ratio) * avg_len

        return {
            "distinct_ratio": distinct_ratio,
            "avg_len": avg_len,
            "collision": collision,
            "p1": p1,
            "p2": p2,
            "p3": p3,
            "elcp": elcp,
            "strength": strength,
        }

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

        # Normalize to string with empty for NaN
        df2 = df2.copy()
        df2 = df2.fillna("")
        try:
            df2 = df2.astype(str, copy=False)
        except Exception:
            df2 = df2.astype(str)

        cols = list(df2.columns)
        m = len(cols)
        n = len(df2)

        if m <= 1 or n <= 1:
            return df2

        stats = {}
        for c in cols:
            stats[c] = self._col_stats(df2[c], k_pref=3)

        # Initial global ordering by per-column strength
        init_order = sorted(cols, key=lambda c: stats[c]["strength"], reverse=True)

        # Greedy refine early columns using exact-duplicate preservation on sample
        if n > 0 and m > 2:
            sample_size = 8000
            if early_stop is not None and early_stop > 0:
                sample_size = min(sample_size, max(2000, int(early_stop // 10)))
            sample_size = min(sample_size, n)

            rng = np.random.default_rng(0)
            if sample_size < n:
                sample_idx = rng.choice(n, size=sample_size, replace=False)
            else:
                sample_idx = np.arange(n, dtype=np.int64)

            MASK = (1 << 64) - 1
            P = np.uint64(11400714819323198485)

            col_hash = {}
            for c in cols:
                a = df2[c].to_numpy(dtype=object, copy=False)[sample_idx]
                h = np.fromiter(((hash(x) & MASK) for x in a), dtype=np.uint64, count=sample_size)
                col_hash[c] = h

            prefix_target = min(m, max(8, min(18, int(m * 0.30) + 6)))
            selected = []
            remaining = init_order.copy()

            current = np.zeros(sample_size, dtype=np.uint64)

            for step in range(prefix_target):
                if not remaining:
                    break
                base = current * P

                best_c = None
                best_score = -1e300
                best_new = None
                best_share = 0.0

                for c in remaining:
                    h_new = base + col_hash[c]
                    _, cnt = np.unique(h_new, return_counts=True)
                    dup = int(cnt[cnt > 1].sum())
                    share = float(dup) / float(sample_size) if sample_size else 0.0

                    st = stats[c]
                    score = (
                        share * (1.0 + min(32.0, st["avg_len"]) + 0.75 * st["elcp"])
                        + 0.05 * st["strength"]
                        - 0.15 * st["distinct_ratio"]
                    )

                    if score > best_score:
                        best_score = score
                        best_c = c
                        best_new = h_new
                        best_share = share

                if best_c is None:
                    break

                selected.append(best_c)
                current = best_new
                remaining.remove(best_c)

                if step >= 8 and best_share < 0.02:
                    break

            rest = [c for c in init_order if c not in set(selected)]
            rest_sorted = sorted(rest, key=lambda c: stats[c]["strength"], reverse=True)

            low = [c for c in rest_sorted if stats[c]["distinct_ratio"] <= distinct_value_threshold]
            high = [c for c in rest_sorted if stats[c]["distinct_ratio"] > distinct_value_threshold]

            final_order = selected + low + high
        else:
            rest_sorted = init_order
            low = [c for c in rest_sorted if stats[c]["distinct_ratio"] <= distinct_value_threshold]
            high = [c for c in rest_sorted if stats[c]["distinct_ratio"] > distinct_value_threshold]
            final_order = low + high

        # Safety: include all columns exactly once
        seen = set()
        final_cols = []
        for c in final_order:
            if c in df2.columns and c not in seen:
                seen.add(c)
                final_cols.append(c)
        for c in df2.columns:
            if c not in seen:
                final_cols.append(c)

        return df2.reindex(columns=final_cols)
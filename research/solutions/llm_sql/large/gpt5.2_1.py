import numpy as np
import pandas as pd
from typing import List, Optional, Any, Dict, Tuple


class Solution:
    def _make_unique_name(self, existing: set, base: str) -> str:
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

    def _normalize_merge_groups(self, df: pd.DataFrame, col_merge: list) -> List[List[str]]:
        if not col_merge:
            return []
        original_cols = list(df.columns)
        groups = []
        for grp in col_merge:
            if grp is None:
                continue
            if not isinstance(grp, (list, tuple)):
                grp = [grp]
            names = []
            for x in grp:
                if isinstance(x, (int, np.integer)):
                    xi = int(x)
                    if 0 <= xi < len(original_cols):
                        names.append(original_cols[xi])
                else:
                    names.append(str(x))
            names = [c for c in names if c in df.columns]
            # de-duplicate while preserving order
            seen = set()
            norm = []
            for c in names:
                if c not in seen:
                    seen.add(c)
                    norm.append(c)
            if len(norm) >= 2:
                groups.append(norm)
        return groups

    def _apply_merges(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        groups = self._normalize_merge_groups(df, col_merge)
        if not groups:
            return df

        df2 = df.copy(deep=False)
        existing = set(df2.columns)

        for cols in groups:
            cols_present = [c for c in cols if c in df2.columns]
            if len(cols_present) < 2:
                continue

            pos = df2.columns.get_loc(cols_present[0])
            base = "MERGED_" + "_".join(str(c) for c in cols_present)
            if len(base) > 120:
                base = base[:120]
            new_name = self._make_unique_name(existing, base)

            merged = df2[cols_present].astype(str).agg("".join, axis=1)
            df2 = df2.drop(columns=cols_present)
            df2.insert(pos, new_name, merged)

        return df2

    def _sample_indices(self, n: int, s: int) -> np.ndarray:
        if s >= n:
            return np.arange(n, dtype=np.int64)
        if s <= 1:
            return np.array([0], dtype=np.int64)
        return np.linspace(0, n - 1, num=s, dtype=np.int64)

    def _combine_keys(self, cur: np.ndarray, codes: np.ndarray) -> np.ndarray:
        # uint64 rolling hash
        P = np.uint64(11400714819323198485)  # 2^64 / golden ratio
        x = (cur.astype(np.uint64) * P) + (codes.astype(np.uint64) + np.uint64(1))
        x ^= (x >> np.uint64(33))
        x *= np.uint64(0xff51afd7ed558ccd)
        x ^= (x >> np.uint64(33))
        return x

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
        if df is None or df.shape[1] <= 1 or df.shape[0] <= 1:
            if col_merge:
                return self._apply_merges(df, col_merge)
            return df

        dfm = self._apply_merges(df, col_merge)
        n = int(dfm.shape[0])
        cols = list(dfm.columns)
        m = len(cols)
        if m <= 1:
            return dfm

        # sample for stats and greedy evaluation
        sample_size = min(n, 4096)
        idx = self._sample_indices(n, sample_size)
        dfs = dfm.iloc[idx]

        codes_map: Dict[str, np.ndarray] = {}
        distinct_ratio: Dict[str, float] = {}
        avg_len: Dict[str, float] = {}
        base_gain: Dict[str, float] = {}
        prefix_score: Dict[str, float] = {}

        S = int(sample_size)
        k_prefixes = (1, 2, 3)

        for c in cols:
            arr = dfs[c].astype(str).to_numpy()
            # factorize full strings
            full_codes, uniques = pd.factorize(arr, sort=False)
            full_codes = full_codes.astype(np.int32, copy=False)
            codes_map[c] = full_codes

            uniq_full = int(len(uniques))
            dr = float(uniq_full) / float(S) if S > 0 else 1.0
            distinct_ratio[c] = dr

            # avg length
            # (python len loop is fine for 4k)
            total_len = 0
            for s in arr:
                total_len += len(s)
            al = float(total_len) / float(S) if S > 0 else 0.0
            avg_len[c] = al

            dup_full = float(S - uniq_full)
            bg = dup_full * al
            base_gain[c] = bg

            # partial prefix sharing (used lightly)
            best_ps = 0.0
            for k in k_prefixes:
                pref = np.fromiter((s[:k] for s in arr), dtype=object, count=S)
                _, u = pd.factorize(pref, sort=False)
                dup_k = float(S - len(u))
                ps = dup_k * float(k)
                if ps > best_ps:
                    best_ps = ps
            prefix_score[c] = best_ps

        remaining = set(cols)
        selected: List[str] = []
        cur_key = np.zeros(S, dtype=np.uint64)

        max_greedy = min(m, max(8, 8 * int(col_stop) + 4))
        stop_dup_frac = 0.02

        for step in range(max_greedy):
            best_col = None
            best_gain = -1.0

            # If remaining is large and step is not too small, optionally restrict to promising subset
            # to reduce work on very high-distinct columns.
            if step < 6:
                candidates = list(remaining)
            else:
                # keep all low-distinct plus top by base_gain
                low = [c for c in remaining if distinct_ratio[c] <= max(0.90, distinct_value_threshold)]
                if len(low) < 12:
                    # add top by base_gain
                    others = sorted(remaining, key=lambda x: base_gain[x], reverse=True)
                    candidates = list(dict.fromkeys(low + others[:24]))
                else:
                    candidates = low

            for c in candidates:
                new_key = self._combine_keys(cur_key, codes_map[c])
                uniq = int(np.unique(new_key).size)
                dup = float(S - uniq)
                gain = dup * avg_len[c]
                if step == 0:
                    gain += 0.05 * prefix_score[c]
                if gain > best_gain:
                    best_gain = gain
                    best_col = c

            if best_col is None or best_gain <= 0.0:
                break

            selected.append(best_col)
            remaining.remove(best_col)
            cur_key = self._combine_keys(cur_key, codes_map[best_col])

            if step >= 3:
                uniq_cur = int(np.unique(cur_key).size)
                dup_cur = float(S - uniq_cur)
                if dup_cur < float(S) * stop_dup_frac:
                    break

            if not remaining:
                break

        def rem_sort_key(c: str) -> Tuple[int, float, float, float, str]:
            # high-distinct to the end; within group put lower distinct first; then higher base gain/len
            high = 1 if distinct_ratio[c] >= distinct_value_threshold else 0
            return (high, distinct_ratio[c], -base_gain[c], -avg_len[c], c)

        remaining_sorted = sorted(list(remaining), key=rem_sort_key)
        final_order = selected + remaining_sorted

        # Safety: preserve any columns that might have been missed (shouldn't happen)
        if len(final_order) != m:
            seen = set(final_order)
            for c in cols:
                if c not in seen:
                    final_order.append(c)

        return dfm.loc[:, final_order]
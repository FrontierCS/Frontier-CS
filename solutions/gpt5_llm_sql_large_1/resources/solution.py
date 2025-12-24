import pandas as pd
import numpy as np
import math
from typing import List, Any, Dict, Tuple, Optional


class Solution:
    def _resolve_merge_group(self, group: list, original_cols: List[Any]) -> List[Any]:
        resolved = []
        for x in group:
            if isinstance(x, (int, np.integer)):
                idx = int(x)
                if 0 <= idx < len(original_cols):
                    resolved.append(original_cols[idx])
            else:
                resolved.append(x)
        seen = set()
        out = []
        for c in resolved:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def _unique_col_name(self, cols: List[Any], base: str) -> str:
        if base not in cols:
            return base
        k = 1
        while True:
            name = f"{base}__m{k}"
            if name not in cols:
                return name
            k += 1

    def _apply_col_merges(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        df2 = df.copy()
        original_cols = list(df.columns)

        for group in col_merge:
            if not group or not isinstance(group, (list, tuple)):
                continue
            names = self._resolve_merge_group(group, original_cols)
            names = [c for c in names if c in df2.columns]
            if len(names) <= 1:
                continue

            insert_pos = min(int(df2.columns.get_loc(c)) for c in names)
            merged = df2[names[0]].astype(str)
            for c in names[1:]:
                merged = merged + df2[c].astype(str)

            base_name = "+".join(str(c) for c in names)
            new_name = self._unique_col_name(list(df2.columns), base_name)

            df2 = df2.drop(columns=names)
            df2.insert(insert_pos, new_name, merged)

        return df2

    def _col_stats(self, ser: pd.Series, K: int = 8) -> Tuple[float, float, float, float]:
        arr = ser.astype(str).to_numpy(dtype=object, copy=False)
        n = int(len(arr))
        if n <= 1:
            avg_len = float(len(arr[0])) if n == 1 else 0.0
            return avg_len, 1.0, avg_len, 0.0

        lens = np.fromiter((len(x) for x in arr), dtype=np.int32, count=n)
        avg_len = float(lens.mean())

        vc = pd.Series(arr, copy=False).value_counts(dropna=False)
        counts = vc.to_numpy(dtype=np.int64, copy=False)
        n2 = float(n) * float(n)
        sumsq = float(np.dot(counts, counts))
        g_full = sumsq / n2

        uniq_vals = vc.index.to_numpy(dtype=object, copy=False)
        tail_lens = np.fromiter((max(0, len(v) - K) for v in uniq_vals), dtype=np.int32, count=len(uniq_vals))
        tail = float(np.dot(counts * counts, tail_lens.astype(np.int64, copy=False))) / n2

        e_prefix = 0.0
        max_k = min(K, int(lens.max()) if n > 0 else 0)
        if max_k > 0:
            for k in range(1, max_k + 1):
                mask = lens >= k
                if not mask.any():
                    continue
                d: Dict[str, int] = {}
                for s in arr[mask]:
                    p = s[:k]
                    d[p] = d.get(p, 0) + 1
                s2 = 0
                for c in d.values():
                    s2 += c * c
                e_prefix += float(s2) / n2

        e_total = e_prefix + tail
        distinct_ratio = float(len(vc)) / float(n)
        return avg_len, g_full, e_total, distinct_ratio

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
        df2 = self._apply_col_merges(df, col_merge)

        cols = list(df2.columns)
        m = len(cols)
        if m <= 1:
            return df2

        n = len(df2)
        sample_n = min(n, 4000)
        if n <= sample_n:
            sdf = df2
        else:
            sdf = df2.sample(n=sample_n, random_state=0)

        K = 8
        keys: List[Tuple[float, float, float, int, Any]] = []
        for idx, c in enumerate(cols):
            avg_len, g_full, e_total, distinct_ratio = self._col_stats(sdf[c], K=K)

            if g_full >= 1.0 - 1e-15:
                key = float("inf")
            else:
                key = e_total / max(1e-12, (1.0 - g_full))

            if distinct_ratio > distinct_value_threshold and not math.isinf(key):
                key *= 0.5

            keys.append((key, e_total, g_full, -idx, c))

        keys.sort(reverse=True)
        new_order = [c for (_, _, _, _, c) in keys]
        return df2.loc[:, new_order]

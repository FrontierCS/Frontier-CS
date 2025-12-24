import pandas as pd
import numpy as np
from typing import List, Any, Dict, Tuple, Optional


class Solution:
    def _normalize_merge_group(self, df: pd.DataFrame, group: Any) -> List[Any]:
        cols = list(df.columns)
        out = []
        seen = set()
        if group is None:
            return out
        if not isinstance(group, (list, tuple)):
            group = [group]
        for x in group:
            col = None
            if x in df.columns:
                col = x
            elif isinstance(x, (int, np.integer)):
                xi = int(x)
                if 0 <= xi < len(cols):
                    col = cols[xi]
                elif 1 <= xi <= len(cols):
                    col = cols[xi - 1]
            else:
                try:
                    xs = str(x)
                    if xs in df.columns:
                        col = xs
                except Exception:
                    col = None
            if col is not None and col not in seen:
                out.append(col)
                seen.add(col)
        return out

    def _unique_merged_name(self, df: pd.DataFrame, group_cols: List[Any]) -> Any:
        base = "__".join(str(c) for c in group_cols)
        name = base
        k = 1
        while name in df.columns:
            name = f"{base}__m{k}"
            k += 1
        return name

    def _apply_column_merges(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        df_work = df
        for group in col_merge:
            group_cols = self._normalize_merge_group(df_work, group)
            if len(group_cols) <= 1:
                continue

            curr_cols = list(df_work.columns)
            present = [c for c in group_cols if c in df_work.columns]
            if len(present) <= 1:
                continue

            new_name = self._unique_merged_name(df_work, present)

            arrays = []
            for c in present:
                s = df_work[c]
                try:
                    arr = s.to_numpy(dtype=str, copy=False)
                except Exception:
                    arr = s.astype(str).to_numpy()
                arrays.append(arr)

            merged = arrays[0]
            for arr in arrays[1:]:
                merged = np.char.add(merged, arr)

            merged_series = pd.Series(merged, index=df_work.index, name=new_name)

            df_work = df_work.drop(columns=present)
            df_work[new_name] = merged_series

            new_cols = []
            inserted = False
            present_set = set(present)
            for c in curr_cols:
                if c in present_set:
                    if not inserted:
                        new_cols.append(new_name)
                        inserted = True
                    continue
                if c in df_work.columns:
                    new_cols.append(c)
            if not inserted:
                new_cols.append(new_name)

            df_work = df_work[new_cols]

        return df_work

    def _column_stats(self, values: np.ndarray, lmax: int) -> Tuple[float, float, float, float]:
        n = int(values.shape[0])
        if n <= 1:
            s = values[0] if n == 1 else ""
            sl = len(s)
            return 1.0, float(sl), 0.0, float(sl)

        denom = float(n * n)

        cnt: Dict[Any, int] = {}
        pref_cnts: List[Dict[Any, int]] = [dict() for _ in range(lmax)]
        total_len = 0

        cnt_get = cnt.get
        pref_gets = [d.get for d in pref_cnts]
        for v in values:
            try:
                s = v if isinstance(v, str) else str(v)
            except Exception:
                s = ""
            ls = len(s)
            total_len += ls

            cnt[s] = cnt_get(s, 0) + 1

            ml = lmax if ls >= lmax else ls
            if ml <= 0:
                continue
            if ml >= 1:
                p = s[:1]
                d = pref_cnts[0]
                d[p] = pref_gets[0](p, 0) + 1
            if ml >= 2:
                p = s[:2]
                d = pref_cnts[1]
                d[p] = pref_gets[1](p, 0) + 1
            if ml >= 3:
                p = s[:3]
                d = pref_cnts[2]
                d[p] = pref_gets[2](p, 0) + 1
            if ml >= 4:
                p = s[:4]
                d = pref_cnts[3]
                d[p] = pref_gets[3](p, 0) + 1
            if ml >= 5:
                p = s[:5]
                d = pref_cnts[4]
                d[p] = pref_gets[4](p, 0) + 1
            if ml >= 6:
                p = s[:6]
                d = pref_cnts[5]
                d[p] = pref_gets[5](p, 0) + 1

        sumsq = 0
        for c in cnt.values():
            sumsq += c * c
        p_full = float(sumsq) / denom

        c_pref = 0.0
        for d in pref_cnts:
            if not d:
                continue
            ss = 0
            for c in d.values():
                ss += c * c
            c_pref += float(ss) / denom

        avg_len = float(total_len) / float(n)
        tail = avg_len - float(lmax)
        if tail > 0.0 and p_full > 0.0:
            c_lcp = c_pref + tail * p_full
        else:
            c_lcp = c_pref

        distinct_ratio = float(len(cnt)) / float(n)
        return p_full, c_lcp, distinct_ratio, avg_len

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

        df_work = self._apply_column_merges(df.copy(), col_merge)

        N = int(df_work.shape[0])
        cols = list(df_work.columns)
        M = len(cols)
        if M <= 1:
            return df_work

        n_s = min(N, 6000)
        if n_s <= 0:
            return df_work

        if n_s == N:
            idx = None
        else:
            idx = np.linspace(0, N - 1, n_s, dtype=np.int32)

        lmax = 6
        gamma = 0.35
        eps = 1e-9

        col_scores: List[Tuple[float, float, float, float, int, Any]] = []
        for j, c in enumerate(cols):
            s = df_work[c]
            try:
                if idx is None:
                    vals = s.to_numpy(dtype=str, copy=False)
                else:
                    vals = s.iloc[idx].to_numpy(dtype=str, copy=False)
            except Exception:
                if idx is None:
                    vals = s.astype(str).to_numpy()
                else:
                    vals = s.iloc[idx].astype(str).to_numpy()

            p_full, c_lcp, distinct_ratio, avg_len = self._column_stats(vals, lmax)

            if p_full >= 1.0 - 1e-15:
                base_key = float("inf")
                score = float("inf")
            else:
                base_key = c_lcp / (1.0 - p_full + eps)
                score = base_key * ((p_full + 1e-12) ** gamma)

            if distinct_ratio > distinct_value_threshold:
                over = (distinct_ratio - distinct_value_threshold) / max(1e-9, (1.0 - distinct_value_threshold))
                pen = max(0.03, (1.0 - over))
                score *= pen * pen

            cname = str(c).lower()
            if ("id" in cname or "uuid" in cname) and distinct_ratio > 0.4:
                score *= 0.08

            if distinct_ratio > 0.95 and p_full < 0.002:
                score *= 0.02

            col_scores.append((score, base_key, p_full, avg_len, j, c))

        col_scores.sort(key=lambda x: (x[0], x[1], x[2], x[3], -x[4]), reverse=True)
        ordered_cols = [c for _, _, _, _, _, c in col_scores]

        return df_work[ordered_cols]

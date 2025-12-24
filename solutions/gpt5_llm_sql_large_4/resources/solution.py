import numpy as np
import pandas as pd


class Solution:
    def _resolve_merge_group(self, df: pd.DataFrame, group, orig_cols):
        resolved = []
        seen = set()
        for item in group:
            col = None
            if isinstance(item, str):
                if item in df.columns:
                    col = item
            elif isinstance(item, (int, np.integer)):
                idx = int(item)
                if 0 <= idx < len(orig_cols):
                    name = orig_cols[idx]
                    if name in df.columns:
                        col = name
            if col is not None and col not in seen:
                resolved.append(col)
                seen.add(col)
        return resolved

    def _apply_col_merge(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df = df.copy()
        orig_cols = list(df.columns)

        for group in col_merge:
            if not group or not isinstance(group, (list, tuple)):
                continue
            cols = self._resolve_merge_group(df, group, orig_cols)
            if len(cols) <= 1:
                continue

            pos = None
            for c in cols:
                try:
                    loc = df.columns.get_loc(c)
                    pos = loc if pos is None else min(pos, loc)
                except Exception:
                    continue
            if pos is None:
                continue

            merged = df[cols[0]].astype(str)
            for c in cols[1:]:
                merged = merged + df[c].astype(str)

            base_name = "__".join(map(str, cols))
            new_name = base_name
            if new_name in df.columns:
                k = 1
                while f"{base_name}__m{k}" in df.columns:
                    k += 1
                new_name = f"{base_name}__m{k}"

            df = df.drop(columns=cols)
            df.insert(pos, new_name, merged)

        return df

    @staticmethod
    def _combine_hash(cur: np.ndarray, codes: np.ndarray) -> np.ndarray:
        # cur, codes are uint64
        # simple 64-bit mixing; collisions are possible but unlikely for N<=30k
        return cur * np.uint64(6364136223846793005) + codes * np.uint64(1442695040888963407) + np.uint64(0x9E3779B97F4A7C15)

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
        N = int(len(df2))
        M = len(cols)
        if M <= 1 or N <= 1:
            return df2

        sample_n = min(N, 2000)
        if sample_n < N:
            rs = np.random.RandomState(0)
            sample_idx = rs.choice(N, size=sample_n, replace=False)
        else:
            sample_idx = np.arange(N)

        nunique = {}
        distinct_ratio = {}
        mean_len = {}
        base_score = {}

        N_float = float(N)
        for c in cols:
            s = df2[c]
            try:
                nu = int(s.nunique(dropna=False))
            except Exception:
                nu = int(pd.Series(s).nunique(dropna=False))
            nunique[c] = nu
            dr = nu / N_float if N > 0 else 1.0
            distinct_ratio[c] = dr

            try:
                ml = s.iloc[sample_idx].astype(str).str.len().mean()
                if ml is None or not np.isfinite(ml):
                    ml = 0.0
            except Exception:
                try:
                    arr = pd.Series(s.iloc[sample_idx]).astype(str).to_numpy()
                    ml = float(np.mean([len(x) for x in arr]))
                except Exception:
                    ml = 0.0
            ml = float(ml)
            mean_len[c] = ml
            base_score[c] = ml * float(N - nu)

        cols_by_base = sorted(cols, key=lambda c: base_score[c], reverse=True)

        L = min(M, max(18, int(M * 0.35)))
        cand_set = set(cols_by_base[:L])
        for c in cols:
            if distinct_ratio[c] <= distinct_value_threshold:
                cand_set.add(c)
        candidates = [c for c in cols_by_base if c in cand_set]

        # Precompute factor codes for candidates only (uint64, nonzero)
        codes = {}
        for c in candidates:
            arr = df2[c].to_numpy()
            try:
                code, _ = pd.factorize(arr, sort=False)
            except Exception:
                code, _ = pd.factorize(pd.Series(arr), sort=False)
            code = (code.astype(np.int64) + 1).astype(np.uint64)
            codes[c] = code

        # Greedy choose early columns
        K = min(M, 10)
        selected = []
        used = set()
        cur = np.zeros(N, dtype=np.uint64)
        remaining_cands = set(candidates)

        for pos in range(K):
            if not remaining_cands:
                break

            eval_list = sorted(remaining_cands, key=lambda c: base_score[c], reverse=True)
            if len(eval_list) > 30:
                eval_list = eval_list[:30]

            best = None
            best_gain = -1.0
            best_new = None

            for c in eval_list:
                new = self._combine_hash(cur, codes[c])
                try:
                    uniq = np.unique(new).size
                except Exception:
                    uniq = len(pd.unique(new))
                gain = mean_len[c] * float(N - int(uniq))
                if gain > best_gain + 1e-9:
                    best_gain = gain
                    best = c
                    best_new = new

            if best is None:
                break
            if best_gain <= 0.0 and pos >= 3:
                break

            selected.append(best)
            used.add(best)
            remaining_cands.remove(best)
            cur = best_new

        orig_idx = {c: i for i, c in enumerate(cols)}
        remaining = [c for c in cols if c not in used]
        remaining_sorted = sorted(
            remaining,
            key=lambda c: (distinct_ratio.get(c, 1.0), -base_score.get(c, 0.0), orig_idx.get(c, 10**9)),
        )

        order = selected + remaining_sorted
        # Ensure all columns exactly once
        if len(order) != M or len(set(order)) != M:
            seen = set()
            order2 = []
            for c in order:
                if c in df2.columns and c not in seen:
                    order2.append(c)
                    seen.add(c)
            for c in cols:
                if c in df2.columns and c not in seen:
                    order2.append(c)
                    seen.add(c)
            order = order2

        return df2[order]

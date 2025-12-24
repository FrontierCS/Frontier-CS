import re
import numpy as np
import pandas as pd


class Solution:
    _ID_RE = re.compile(r"(^|[^a-z0-9])(id|uuid|guid)([^a-z0-9]|$)", re.IGNORECASE)

    @staticmethod
    def _safe_colname(existing, base):
        if base not in existing:
            return base
        i = 2
        while True:
            name = f"{base}_{i}"
            if name not in existing:
                return name
            i += 1

    @staticmethod
    def _col_to_u(series: pd.Series) -> np.ndarray:
        # Use pandas' string conversion semantics
        return series.astype(str).to_numpy(dtype="U", copy=True)

    @staticmethod
    def _gini_from_codes(codes: np.ndarray, n: int) -> float:
        if n <= 0:
            return 0.0
        if codes.dtype.kind not in ("i", "u"):
            codes = codes.astype(np.int64, copy=False)
        if codes.size == 0:
            return 0.0
        if codes.min(initial=0) < 0:
            codes = codes[codes >= 0]
        if codes.size == 0:
            return 0.0
        counts = np.bincount(codes)
        p = counts / float(n)
        return float(np.dot(p, p))

    @staticmethod
    def _counts_from_codes(codes: np.ndarray) -> np.ndarray:
        if codes.size == 0:
            return np.zeros(0, dtype=np.int64)
        if codes.min(initial=0) < 0:
            codes = codes[codes >= 0]
        if codes.size == 0:
            return np.zeros(0, dtype=np.int64)
        return np.bincount(codes)

    @staticmethod
    def _expected_lcp(arr_u: np.ndarray, lens: np.ndarray, K: int = 4):
        n = int(arr_u.shape[0])
        if n <= 1:
            return 0.0, 0.0, 1.0, float(lens.mean()) if n > 0 else 0.0

        codes, uniques = pd.factorize(arr_u, sort=False)
        counts = Solution._counts_from_codes(codes)
        inv_n = 1.0 / float(n)
        p = counts * inv_n
        gini_full = float(np.dot(p, p))
        distinct_ratio = float(len(uniques) * inv_n)
        avg_len = float(lens.mean())

        # Expected truncated LCP for first K chars:
        # E[min(LCP, K)] = sum_{k=1..K} P(LCP >= k)
        # P(LCP >= k) = sum_{prefix_k} (count(prefix_k)/n)^2 with only strings len>=k.
        exp_trunc = 0.0
        for k in range(1, K + 1):
            mask = lens >= k
            mk = int(mask.sum())
            if mk <= 1:
                continue
            sub = arr_u[mask]
            pref = np.fromiter((x[:k] for x in sub), dtype=f"<U{k}", count=mk)
            pcodes, _ = pd.factorize(pref, sort=False)
            pcounts = Solution._counts_from_codes(pcodes)
            pp = pcounts * inv_n
            exp_trunc += float(np.dot(pp, pp))

        # Extra beyond K only when values are fully equal:
        # extra = sum_{val} (freq(val)/n)^2 * max(len(val) - K, 0)
        if len(uniques) > 0:
            uniques_u = np.array(uniques, dtype="U", copy=False)
            u_lens = np.char.str_len(uniques_u).astype(np.int32, copy=False)
            extra = float(np.dot((counts * inv_n) ** 2, np.maximum(u_lens - K, 0)))
        else:
            extra = 0.0

        exp_lcp = exp_trunc + extra
        return exp_lcp, gini_full, distinct_ratio, avg_len

    def _apply_merges(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df2 = df.copy(deep=False)
        original_cols = list(df2.columns)
        existing = set(original_cols)

        for group in col_merge:
            if not group or len(group) < 2:
                continue

            group_names = []
            for c in group:
                if isinstance(c, (int, np.integer)):
                    idx = int(c)
                    if 0 <= idx < len(original_cols):
                        group_names.append(original_cols[idx])
                else:
                    group_names.append(c)

            # Deduplicate while preserving order
            seen = set()
            group_names = [c for c in group_names if not (c in seen or seen.add(c))]
            group_names = [c for c in group_names if c in df2.columns]
            if len(group_names) < 2:
                continue

            cols_list = list(df2.columns)
            pos = min(cols_list.index(c) for c in group_names)

            merged_base = "|".join(map(str, group_names))
            merged_name = self._safe_colname(existing, merged_base)
            existing.add(merged_name)

            arr = self._col_to_u(df2[group_names[0]])
            for c in group_names[1:]:
                arr = np.char.add(arr, self._col_to_u(df2[c]))
            merged_series = pd.Series(arr, index=df2.index, name=merged_name)

            df2 = df2.drop(columns=group_names)
            df2.insert(pos, merged_name, merged_series)

        return df2

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
        df2 = self._apply_merges(df, col_merge)
        cols = list(df2.columns)
        n_rows = len(df2)
        if n_rows <= 1 or len(cols) <= 1:
            return df2

        sample_n = min(n_rows, int(early_stop) if early_stop else n_rows, 10000)
        if sample_n < 500:
            sample_n = min(n_rows, 500)

        sample = df2.iloc[:sample_n]

        col_infos = []
        for idx, col in enumerate(cols):
            name = str(col)
            arr = self._col_to_u(sample[col])
            lens = np.char.str_len(arr).astype(np.int32, copy=False)

            exp_lcp, gini_full, distinct_ratio, avg_len = self._expected_lcp(arr, lens, K=4)

            # Ordering metric derived from pairwise swap condition for:
            # sum exp_i * product prev_p, where prev_p is exact-match prob (gini_full).
            metric = exp_lcp / (1.0 - gini_full + 1e-6)

            lname = name.lower()
            idlike = (distinct_ratio >= 0.98) and (lname == "id" or self._ID_RE.search(lname) is not None)

            # Buckets: low distinct first, then high distinct, then id-like at end
            if idlike:
                bucket = 2
            else:
                bucket = 0 if distinct_ratio <= float(distinct_value_threshold) else 1

            col_infos.append(
                (
                    bucket,
                    -metric,
                    -exp_lcp,
                    distinct_ratio,
                    -avg_len,
                    idx,
                    col,
                )
            )

        col_infos.sort()
        new_cols = [t[-1] for t in col_infos]
        return df2.loc[:, new_cols]

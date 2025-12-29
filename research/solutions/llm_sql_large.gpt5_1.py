import pandas as pd
import numpy as np
import math


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
        # Step 1: Optional column merges
        def apply_col_merges(df_in: pd.DataFrame, merges):
            if not merges:
                return df_in
            dfm = df_in.copy()
            for idx, group in enumerate(merges):
                if not group:
                    continue
                valid = [c for c in group if c in dfm.columns]
                if len(valid) <= 1:
                    continue
                # Merge by string concatenation without spaces
                try:
                    merged_series = dfm[valid].astype(str).agg(''.join, axis=1)
                except Exception:
                    # Fallback: slower but robust
                    merged_series = dfm[valid].apply(lambda r: ''.join([str(x) for x in r.values]), axis=1)
                new_col = f"_MERGED_{idx}"
                dfm = dfm.drop(columns=valid)
                dfm[new_col] = merged_series
            return dfm

        df_work = apply_col_merges(df, col_merge)

        # Parameters and sampling
        N = len(df_work)
        if N == 0 or df_work.shape[1] <= 1:
            return df_work

        sample_n = min(N, early_stop if early_stop is not None else N)
        # Use first sample_n rows deterministically
        sample_idx = np.arange(sample_n)

        cols = list(df_work.columns)
        M = len(cols)

        # Precompute factorized codes and base per column on sample
        codes_dict = {}
        base_dict = {}
        uniq_counts = {}
        avg_len = {}

        for c in cols:
            s = df_work[c].iloc[sample_idx]
            # Factorize with NaN support -> -1, shift to 0..K
            codes, uniques = pd.factorize(s, sort=False, na_sentinel=-1)
            # shift by +1 to make NaN=0, others 1..K
            codes = (codes + 1).astype(np.int64, copy=False)
            max_code = int(codes.max()) if codes.size > 0 else 0
            base = max_code + 1  # ensure base > max_code
            if base <= 0:
                base = 1
            codes_dict[c] = codes
            base_dict[c] = base
            uniq_counts[c] = len(uniques) + (1 if (codes == 0).any() else 0)

            # Estimate average string length on sample
            try:
                avg_len[c] = float(s.astype(str).str.len().mean())
            except Exception:
                # Robust fallback
                avg_len[c] = float(np.mean([len(str(x)) for x in s]))

            if not np.isfinite(avg_len[c]):
                avg_len[c] = 0.0

        # Greedy construction of column order maximizing dup_frac(prefix)*len(column)
        gid = np.zeros(sample_n, dtype=np.int64)  # current prefix group id over sample
        selected = []
        remaining = set(cols)

        # Precompute initial duplicates fraction per column alone for tie-breaks
        dup_frac_alone = {}
        for c in cols:
            # Since gid are zeros, newkey == codes
            u = uniq_counts[c] if c in uniq_counts else len(pd.unique(codes_dict[c]))
            dup_frac_alone[c] = max(0.0, 1.0 - (u / sample_n))

        # Greedy loop
        for _ in range(M):
            best_col = None
            best_score = -1.0
            best_base = 1
            # Evaluate candidates
            for c in list(remaining):
                codes_c = codes_dict[c]
                base_c = base_dict[c]
                # Combine keys (gid, codes_c)
                # key = gid * base_c + codes_c
                # We only need the unique count to compute duplicate fraction
                key = gid * base_c + codes_c
                # Use factorize to count unique number of pairs
                # Note: factorize returns (codes, uniques)
                try:
                    uniq = pd.factorize(key, sort=False)[1].size
                except Exception:
                    uniq = np.unique(key).size
                dup_frac = 1.0 - (uniq / sample_n)
                if dup_frac < 0:
                    dup_frac = 0.0
                # Score = duplicates fraction for new prefix times average length of this column
                score = dup_frac * avg_len[c]
                # In ties, prefer column with higher dup_frac alone and longer length
                if score > best_score:
                    best_score = score
                    best_col = c
                    best_base = base_c
            if best_col is None:
                # Should not happen, but append remaining arbitrarily by descending avg length
                rest = sorted(list(remaining), key=lambda x: avg_len.get(x, 0.0), reverse=True)
                selected.extend(rest)
                remaining.clear()
                break

            # Update gid with chosen column
            codes_best = codes_dict[best_col]
            key_best = gid * best_base + codes_best
            gid = pd.factorize(key_best, sort=False)[0].astype(np.int64, copy=False)

            selected.append(best_col)
            remaining.remove(best_col)

        # Return reordered DataFrame
        return df_work.loc[:, selected]
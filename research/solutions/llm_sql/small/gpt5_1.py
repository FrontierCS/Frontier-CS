import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

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
        # 1) Apply column merges
        def apply_merges(df_in: pd.DataFrame, merges: List[List[str]]) -> pd.DataFrame:
            if not merges:
                return df_in
            df_out = df_in.copy()
            used_columns = set()
            for group in merges:
                cols = [c for c in group if c in df_out.columns]
                if not cols:
                    continue
                # Build merged string column
                s = df_out[cols[0]].astype(str)
                for c in cols[1:]:
                    s = s + df_out[c].astype(str)
                # Create a unique merged column name
                base_name = "__MERGED__" + "___".join(cols)
                new_name = base_name
                k = 1
                while new_name in df_out.columns:
                    k += 1
                    new_name = f"{base_name}__{k}"
                # Insert the new column at the position of the first column in the group
                first_idx = df_out.columns.get_loc(cols[0])
                df_out.insert(first_idx, new_name, s)
                # Drop original columns in the group
                df_out.drop(columns=cols, inplace=True)
                used_columns.update(cols)
            return df_out

        df2 = apply_merges(df, col_merge)

        cols = list(df2.columns)
        N = len(df2)
        if N == 0 or len(cols) <= 1:
            return df2

        # 2) Prepare per-column data: string representations, lengths, codes, distincts
        str_series: Dict[str, pd.Series] = {}
        lengths: Dict[str, np.ndarray] = {}
        len_avg: Dict[str, float] = {}
        distinct_count: Dict[str, int] = {}
        codes_by_col: Dict[str, np.ndarray] = {}

        for c in cols:
            s = df2[c].astype(str)
            str_series[c] = s
            ln = s.str.len().to_numpy(np.int32, copy=False)
            lengths[c] = ln
            len_avg[c] = float(ln.mean()) if N > 0 else 0.0
            # Using factorize for codes to later compute unique counts efficiently
            codes = pd.factorize(s, sort=False)[0].astype(np.int32, copy=False)
            codes_by_col[c] = codes
            # Distinct including NaN (string "nan")
            distinct_count[c] = int(pd.unique(s).size)

        # 3) Compute per-column intrinsic char-prefix gain for first position
        #    Use up to K prefix characters per column for efficiency
        #    K determined by row_stop * 4 (default 16), but limited by max length in the column
        def charprefix_gain_for_column(col: str, max_k: int) -> float:
            s = str_series[col]
            ln = lengths[col]
            # We'll sum (N_k - D_k) / N over k=1..K
            # where N_k = count of rows with length >= k
            # and D_k = number of distinct prefixes of length k among those rows
            K = int(max_k)
            if K <= 0:
                return 0.0
            res = 0.0
            for k in range(1, K + 1):
                m = ln >= k
                Nk = int(m.sum())
                if Nk <= 1:
                    # no contribution possible from this k
                    continue
                pref_k = s[m].str.slice(0, k)
                Dk = int(pd.unique(pref_k).size)
                res += float(Nk - Dk) / float(N)
            return res

        # Determine per-column K limit (min of row_stop * 4 and per-column max length, and cap at 24)
        base_K = max(1, int(row_stop) * 4)
        base_K = min(base_K, 24)

        charprefix_gain: Dict[str, float] = {}
        for c in cols:
            max_len_c = int(lengths[c].max()) if N > 0 else 0
            Kc = min(base_K, max_len_c)
            if Kc <= 0:
                charprefix_gain[c] = 0.0
            else:
                charprefix_gain[c] = charprefix_gain_for_column(c, Kc)

        # 4) Helper: count unique rows for a set of columns using codes
        unique_cache: Dict[Tuple[str, ...], int] = {}

        def unique_count_for_columns(col_list: List[str]) -> int:
            key = tuple(sorted(col_list))
            if key in unique_cache:
                return unique_cache[key]
            if len(col_list) == 1:
                arr = codes_by_col[col_list[0]]
                u = int(np.unique(arr).size)
                unique_cache[key] = u
                return u
            arr = np.column_stack([codes_by_col[c] for c in col_list]).astype(np.int32, copy=False)
            # view as contiguous bytes
            arr = np.ascontiguousarray(arr)
            dtype_void = np.dtype((np.void, arr.dtype.itemsize * arr.shape[1]))
            viewed = arr.view(dtype_void).ravel()
            u = int(np.unique(viewed).size)
            unique_cache[key] = u
            return u

        # 5) Select first column: combine intrinsic char-prefix gain with duplicate-based gain
        #    duplicates-based gain for first position is len_avg * (N - distinct)/N
        dup_gain_first: Dict[str, float] = {}
        for c in cols:
            dup_gain_first[c] = len_avg[c] * float(N - distinct_count[c]) / float(N) if N > 0 else 0.0

        # weight between prefix-structure and exact-duplicate gains
        alpha = 0.7
        first_scores = {c: alpha * charprefix_gain[c] + (1.0 - alpha) * dup_gain_first[c] for c in cols}
        first_col = max(cols, key=lambda x: (first_scores[x], -distinct_count[x], len_avg[x]))

        order = [first_col]
        remaining = [c for c in cols if c != first_col]

        # 6) Greedy selection for remaining positions using duplicate-based incremental gain
        # Score for candidate c given prefix P is:
        # gain(c | P) = len_avg[c] * (N - unique_count(P ∪ {c})) / N
        while remaining:
            best_c = None
            best_score = -1.0
            P = order
            for c in remaining:
                uniq = unique_count_for_columns(P + [c])
                gain = len_avg[c] * float(N - uniq) / float(N)
                if gain > best_score:
                    best_score = gain
                    best_c = c
            if best_c is None:
                # fallback if something went wrong
                best_c = remaining[0]
            order.append(best_c)
            remaining.remove(best_c)

        # 7) Return DataFrame with columns in the new order
        return df2[order]
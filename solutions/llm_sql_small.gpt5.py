import pandas as pd
import numpy as np

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
        # Step 1: Apply column merges if specified
        def apply_col_merge(dataframe: pd.DataFrame, merge_spec: list) -> pd.DataFrame:
            if not merge_spec:
                return dataframe
            df_orig = dataframe.copy()
            # Prepare a string version for efficient concatenation (avoids NaN issues)
            df_str = df_orig.fillna('').astype(str)
            orig_cols = list(df_orig.columns)
            used_cols = set()
            new_cols = {}
            for idx, group in enumerate(merge_spec):
                # Resolve column names
                names = []
                for it in group:
                    if isinstance(it, int):
                        if 0 <= it < len(orig_cols):
                            names.append(orig_cols[it])
                    else:
                        if it in df_orig.columns:
                            names.append(it)
                # Filter existing names and remove duplicates
                names = [n for n in dict.fromkeys(names) if n in df_str.columns]
                if not names:
                    continue
                # Concatenate without separator
                s = df_str[names[0]]
                for nm in names[1:]:
                    s = s.str.cat(df_str[nm], na_rep='')
                # Create unique merge column name
                base_name = f"MERGE_{idx}"
                new_name = base_name
                suf = 1
                while new_name in df_orig.columns or new_name in new_cols:
                    new_name = f"{base_name}_{suf}"
                    suf += 1
                new_cols[new_name] = s
                used_cols.update(names)
            # Drop merged columns and add new merged columns
            df_out = df_orig.drop(columns=list(used_cols), errors='ignore').copy()
            for k, v in new_cols.items():
                df_out[k] = v
            return df_out

        df_merged = apply_col_merge(df, col_merge)

        # If 0 or 1 columns, nothing to reorder
        if df_merged.shape[1] <= 1:
            return df_merged

        # String version for scoring computations
        df_s = df_merged.fillna('').astype(str)
        cols = list(df_s.columns)
        N = len(df_s)

        # Early stop sampling (optional): if dataset too large, sample rows to estimate order
        # Keep deterministic behavior: sample first early_stop rows
        if N > early_stop:
            df_s_sample = df_s.iloc[:early_stop].copy()
            N_sample = early_stop
        else:
            df_s_sample = df_s
            N_sample = N

        # Precompute categorical codes for selected-group speed
        codes_map = {}
        uniques_count = {}
        for c in cols:
            cat = pd.Categorical(df_s_sample[c], ordered=False)
            codes_map[c] = cat.codes.astype(np.int32)
            uniques_count[c] = len(cat.categories)

        # Precompute value -> length map per column
        val_len_map = {}
        str_series_map = {}
        for c in cols:
            s = df_s_sample[c]
            str_series_map[c] = s
            uniq_vals = pd.unique(s)
            lengths = pd.Series(uniq_vals).str.len().to_numpy()
            val_len_map[c] = pd.Series(lengths, index=uniq_vals)

        # Precompute a simple char-level prefix score per column (for tie-breaking)
        # E_partial approximated by K-prefix counts squared
        K = max(1, int(row_stop))
        char_prefix_score = {}
        for c in cols:
            s = str_series_map[c]
            score = 0
            # Limit K to reasonable values (avoid very large K)
            max_len = min(int(s.str.len().max()) if len(s) else 0, 12)
            use_k = min(K, max_len) if max_len > 0 else 0
            for k in range(1, use_k + 1):
                pref = s.str.slice(0, k)
                vc = pref.value_counts(dropna=False)
                arr = vc.to_numpy(dtype=np.int64)
                score += int(np.dot(arr, arr))
            char_prefix_score[c] = score

        # Base series of ones for fast groupby count
        base_series = pd.Series(np.ones(N_sample, dtype=np.int8))

        # Greedy selection of columns maximizing sum of squared counts times value length within current groups
        selected = []
        remaining = cols.copy()

        # Helper to compute score for candidate column given currently selected
        def compute_score_for_candidate(cand_col: str) -> (int, int):
            if not selected:
                # Group by only candidate column
                keys = [str_series_map[cand_col]]
            else:
                # Use codes for selected columns plus raw string for candidate
                keys = [codes_map[scol] for scol in selected] + [str_series_map[cand_col]]
            counts = base_series.groupby(keys, sort=False).count()
            cvals = counts.index.get_level_values(-1)
            lengths = val_len_map[cand_col].reindex(cvals).to_numpy()
            arr_counts = counts.to_numpy(dtype=np.int64)
            score = int(np.dot(arr_counts * arr_counts, lengths))
            tie = char_prefix_score.get(cand_col, 0)
            return score, tie

        while remaining:
            best_col = None
            best_score = -1
            best_tie = -1
            # Evaluate each remaining column
            for c in remaining:
                s, t = compute_score_for_candidate(c)
                if s > best_score or (s == best_score and t > best_tie):
                    best_score = s
                    best_tie = t
                    best_col = c
            selected.append(best_col)
            remaining.remove(best_col)

        # Return DataFrame with reordered columns
        return df_merged.loc[:, selected]

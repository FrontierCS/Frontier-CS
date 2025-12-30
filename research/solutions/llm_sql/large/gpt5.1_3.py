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
        # Work on a copy to avoid mutating the input DataFrame
        df_work = df.copy()

        # 1. Apply column merges if specified
        if col_merge:
            for group in col_merge:
                if group is None:
                    continue
                # Ensure group is iterable
                try:
                    group_list = list(group)
                except TypeError:
                    continue
                # Filter to existing columns
                valid_cols = [c for c in group_list if c in df_work.columns]
                if len(valid_cols) <= 1:
                    continue

                base_col = valid_cols[0]
                # Concatenate as strings without separators
                merged_series = df_work[base_col].astype(str)
                for c in valid_cols[1:]:
                    merged_series = merged_series + df_work[c].astype(str)

                # Replace base column with merged content
                df_work[base_col] = merged_series

                # Drop other columns in the group
                drop_cols = [c for c in valid_cols[1:] if c != base_col]
                if drop_cols:
                    df_work = df_work.drop(columns=drop_cols, errors="ignore")

        # If there are 0 or 1 columns, no reordering is needed
        if df_work.shape[1] <= 1 or len(df_work) == 0:
            return df_work

        N_full = len(df_work)
        # Determine number of rows to use for statistics (sampling for speed)
        if early_stop is None or early_stop <= 0:
            sample_n = N_full
        else:
            sample_n = min(N_full, int(early_stop))

        analysis_df = df_work.iloc[:sample_n]

        # 2. Compute per-column distinct value ratios (using sampled rows)
        nunique_series = analysis_df.nunique(dropna=False)
        distinct_ratio_series = nunique_series.astype(float) / float(sample_n)
        distinct_ratio_dict = distinct_ratio_series.to_dict()

        # 3. Compute approximate average string length per column (using sampled rows)
        avg_len_dict = {}
        cols = list(df_work.columns)
        for col in cols:
            series_sample = analysis_df[col]
            try:
                str_vals = series_sample.astype(str)
            except Exception:
                # Fallback, should rarely be needed
                str_vals = series_sample.map(lambda x: "" if x is None else str(x))
            try:
                lengths = str_vals.str.len()
            except Exception:
                # Very rare fallback
                lengths = str_vals.map(lambda x: len(x) if isinstance(x, str) else len(str(x)))
            if len(lengths) > 0:
                mean_len = float(lengths.mean())
                if not np.isfinite(mean_len):
                    mean_len = 0.0
            else:
                mean_len = 0.0
            avg_len_dict[col] = mean_len

        # 4. Heuristics based on column names for likely ID-like columns
        original_index = {col: idx for idx, col in enumerate(cols)}
        potential_id = {}
        for col in cols:
            name = str(col)
            lower = name.lower()
            is_id = False
            if lower == "id":
                is_id = True
            elif lower.startswith("id_"):
                is_id = True
            elif lower.endswith("_id"):
                is_id = True
            elif lower in ("userid", "user_id", "uid"):
                is_id = True
            elif "uuid" in lower or "guid" in lower:
                is_id = True
            elif lower == "index" or lower.endswith("_index"):
                is_id = True
            potential_id[col] = is_id

        # 5. Build sorting key for each column
        def sort_key(col_name: str):
            base_dr = distinct_ratio_dict.get(col_name, 1.0)
            adj = base_dr

            # Push high-distinct columns (likely IDs) towards the back
            if base_dr >= distinct_value_threshold:
                adj += 1.0

            # Additional push for name-based ID-like columns,
            # but only if they are reasonably high-distinct
            if potential_id.get(col_name, False) and base_dr >= 0.5:
                adj += 1.0

            # Use negative avg_len to sort by descending average length
            return (adj, -avg_len_dict.get(col_name, 0.0), original_index[col_name])

        ordered_cols = sorted(cols, key=sort_key)

        # 6. Return DataFrame with reordered columns
        df_out = df_work.loc[:, ordered_cols]
        return df_out
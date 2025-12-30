import pandas as pd
import numpy as np


class Solution:
    def _apply_col_merge_inplace(self, df_work: pd.DataFrame, col_merge, original_cols):
        if not col_merge:
            return
        if original_cols is None:
            original_cols = list(df_work.columns)
        for idx, group in enumerate(col_merge):
            if not group or len(group) < 2:
                continue
            # Map group entries (indices or names) to column names
            group_names = []
            for g in group:
                if isinstance(g, int):
                    if 0 <= g < len(original_cols):
                        name = original_cols[g]
                    else:
                        continue
                else:
                    name = str(g)
                if name not in group_names:
                    group_names.append(name)
            # Keep only columns currently present in df_work
            existing = [name for name in group_names if name in df_work.columns]
            if len(existing) < 2:
                continue
            base_name = existing[0]
            new_name = f"MERGED_{idx}_{base_name}"
            # Ensure uniqueness of new column name
            while new_name in df_work.columns:
                new_name += "_m"
            # Concatenate string representations row-wise
            try:
                new_series = df_work[existing].astype(str).agg(''.join, axis=1)
            except Exception:
                new_series = df_work[existing].applymap(
                    lambda x: '' if x is None or (isinstance(x, float) and np.isnan(x)) else str(x)
                ).agg(''.join, axis=1)
            # Insert new column at the earliest position among merged columns
            positions = [df_work.columns.get_loc(c) for c in existing]
            insert_pos = min(positions)
            df_work.insert(insert_pos, new_name, new_series)
            # Drop original columns
            df_work.drop(columns=existing, inplace=True)

    def _compute_column_scores(
        self,
        df: pd.DataFrame,
        early_stop: int,
        row_stop: int,
        distinct_value_threshold: float,
    ):
        n_rows = len(df)
        scores = {}
        if n_rows == 0:
            for col in df.columns:
                scores[col] = 0.0
            return scores

        # Determine how many rows to sample for statistics
        sample_limit = n_rows
        if early_stop is not None:
            try:
                es = int(early_stop)
                if es > 0:
                    sample_limit = min(sample_limit, es)
            except Exception:
                pass
        if row_stop is not None:
            try:
                rs = int(row_stop)
                if rs > 0:
                    approx = rs * 10000
                    sample_limit = min(sample_limit, approx)
            except Exception:
                pass

        if sample_limit < n_rows:
            indices = np.linspace(0, n_rows - 1, sample_limit, dtype=int)
        else:
            indices = None

        for col in df.columns:
            series = df[col]
            if indices is not None:
                sub = series.iloc[indices]
            else:
                sub = series

            try:
                str_series = sub.astype(str)
            except Exception:
                str_series = sub.map(lambda v: '' if pd.isna(v) else str(v))

            if str_series.empty:
                scores[col] = 0.0
                continue

            lengths = str_series.str.len()
            avg_len = float(lengths.mean())
            if not np.isfinite(avg_len) or avg_len <= 0.0:
                scores[col] = -1e9
                continue

            num_samples = len(str_series)
            if num_samples == 0:
                scores[col] = -1e9
                continue

            nu_total = int(str_series.nunique(dropna=False))
            distinct_ratio = nu_total / num_samples
            dup_ratio = max(0.0, 1.0 - distinct_ratio)

            prefix_len = 3
            prefix_series = str_series.str.slice(0, prefix_len)
            nu_prefix = int(prefix_series.nunique(dropna=False))
            prefix_dist_ratio = nu_prefix / num_samples
            prefix_dup_ratio = max(0.0, 1.0 - prefix_dist_ratio)

            try:
                arr = str_series.to_numpy()
            except Exception:
                arr = np.array(str_series.tolist(), dtype=object)

            if len(arr) > 1:
                eq_mask = arr[1:] == arr[:-1]
                eq_mask = np.asarray(eq_mask, dtype=bool)
                adjacency_ratio = float(eq_mask.mean())
            else:
                adjacency_ratio = 0.0

            base_dup = 0.7 * dup_ratio + 0.3 * prefix_dup_ratio
            if distinct_ratio >= distinct_value_threshold:
                base_dup *= 0.2

            combined_dup = 0.7 * base_dup + 0.3 * adjacency_ratio
            score = combined_dup * avg_len
            scores[col] = float(score)

        return scores

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
        df_work = df.copy()
        original_cols = list(df_work.columns)

        if col_merge:
            self._apply_col_merge_inplace(df_work, col_merge, original_cols)

        if df_work.shape[1] <= 1:
            return df_work

        scores = self._compute_column_scores(
            df_work,
            early_stop=early_stop,
            row_stop=row_stop,
            distinct_value_threshold=distinct_value_threshold,
        )

        # Preserve relative order for columns with identical scores using original positions
        col_positions = {col: idx for idx, col in enumerate(df_work.columns)}
        sorted_cols = sorted(
            df_work.columns,
            key=lambda c: (-scores.get(c, 0.0), col_positions.get(c, 0)),
        )

        return df_work.loc[:, sorted_cols]
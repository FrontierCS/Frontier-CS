import pandas as pd
import numpy as np


class Solution:
    def _normalize_col_merge(self, col_merge, df):
        if not col_merge:
            return []
        orig_cols = list(df.columns)
        col_set = set(orig_cols)
        normalized = []
        for group in col_merge:
            if not group:
                continue
            names = []
            for item in group:
                if isinstance(item, str):
                    if item in col_set:
                        names.append(item)
                elif isinstance(item, int):
                    if 0 <= item < len(orig_cols):
                        col_name = orig_cols[item]
                        if col_name in col_set:
                            names.append(col_name)
            # deduplicate while keeping order
            seen = set()
            final_names = []
            for name in names:
                if name not in seen:
                    seen.add(name)
                    final_names.append(name)
            if final_names:
                normalized.append(final_names)
        return normalized

    def _apply_col_merge(self, df, col_merge):
        if not col_merge:
            return df

        normalized_merge = self._normalize_col_merge(col_merge, df)
        if not normalized_merge:
            return df

        # Only keep groups with at least 2 existing columns
        groups_to_merge = []
        for group in normalized_merge:
            cols_existing = [c for c in group if c in df.columns]
            if len(cols_existing) >= 2:
                groups_to_merge.append(cols_existing)

        if not groups_to_merge:
            return df

        df_work = df.copy()
        merged_cols_set = set()
        new_col_names = []

        for idx, group_cols in enumerate(groups_to_merge):
            # Avoid merging the same column multiple times
            group_to_use = [c for c in group_cols if c in df_work.columns and c not in merged_cols_set]
            if len(group_to_use) < 2:
                continue
            merged_cols_set.update(group_to_use)

            base_new_name = "_MERGED_" + "_".join(str(c) for c in group_to_use)
            new_name = base_new_name
            suffix = 1
            while new_name in df_work.columns or new_name in new_col_names:
                new_name = f"{base_new_name}_{suffix}"
                suffix += 1

            # Concatenate as strings without separator
            to_merge = df_work[group_to_use].astype(str)
            new_series = to_merge.astype(str).agg(''.join, axis=1)
            df_work[new_name] = new_series
            new_col_names.append(new_name)

        if merged_cols_set:
            df_work = df_work.drop(columns=list(merged_cols_set))

        return df_work

    def _compute_column_scores(self, df, distinct_value_threshold):
        n_rows = len(df)
        cols = list(df.columns)
        scores = {}
        for idx, col in enumerate(cols):
            s = df[col]
            if n_rows <= 1:
                adjacency = 0.0
            else:
                try:
                    arr = s.to_numpy()
                    if len(arr) <= 1:
                        adjacency = 0.0
                    else:
                        cmp = arr[1:] == arr[:-1]
                        try:
                            adjacency = float(np.mean(cmp))
                        except Exception:
                            try:
                                adjacency = float(pd.Series(cmp).mean())
                            except Exception:
                                adjacency = 0.0
                except Exception:
                    adjacency = 0.0

            try:
                nunique = s.nunique(dropna=False)
                uniq_ratio = float(nunique) / n_rows if n_rows > 0 else 0.0
            except Exception:
                # Fallback if nunique fails
                uniq_ratio = 1.0

            if uniq_ratio >= distinct_value_threshold:
                base = 0.1 * (1.0 - uniq_ratio) + 0.1 * adjacency
            else:
                base = 0.7 * (1.0 - uniq_ratio) + 0.3 * adjacency

            scores[col] = (base, idx)
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
        # Apply column merges if specified and applicable
        df_work = self._apply_col_merge(df, col_merge)

        if df_work.shape[1] <= 1:
            # Nothing to reorder
            return df_work

        # Compute column scores based on distinct ratios and adjacency
        scores = self._compute_column_scores(df_work, distinct_value_threshold)

        # Sort columns: higher score first, tie-breaker by original index
        cols = list(df_work.columns)
        cols_sorted = sorted(
            cols,
            key=lambda c: (-scores[c][0], scores[c][1])
        )

        # Return DataFrame with reordered columns
        return df_work.loc[:, cols_sorted]
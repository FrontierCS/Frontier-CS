import pandas as pd
import numpy as np
from typing import List, Optional


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[List[List]]) -> pd.DataFrame:
        if not col_merge:
            return df

        df_merged = df.copy()
        original_cols = list(df.columns)

        for group_idx, group in enumerate(col_merge):
            if not group:
                continue

            # Resolve items in group to column names
            resolved_cols = []
            for item in group:
                if isinstance(item, int):
                    if 0 <= item < len(original_cols):
                        col_name = original_cols[item]
                        if col_name in df_merged.columns:
                            resolved_cols.append(col_name)
                else:
                    if item in df_merged.columns:
                        resolved_cols.append(item)

            # Deduplicate while preserving order
            seen = set()
            group_valid = []
            for name in resolved_cols:
                if name not in seen:
                    seen.add(name)
                    group_valid.append(name)

            if len(group_valid) <= 1:
                # Nothing to merge or only one valid column, skip
                continue

            # Generate a unique merged column name
            base_name = f"__merged_{group_idx}__"
            new_name = base_name
            suffix = 1
            while new_name in df_merged.columns:
                suffix += 1
                new_name = f"{base_name}{suffix}"

            # Merge columns by concatenating their string representations row-wise
            merged_series = df_merged[group_valid].astype(str).agg("".join, axis=1)

            # Insert merged column at the position of the first column in the group
            insert_at = df_merged.columns.get_loc(group_valid[0])
            df_merged.drop(columns=group_valid, inplace=True)
            df_merged.insert(insert_at, new_name, merged_series)

        return df_merged

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
        # Work on a copy to avoid mutating the original DataFrame
        df_work = df.copy()

        # Apply column merges if specified
        if col_merge:
            df_work = self._apply_col_merge(df_work, col_merge)

        n_rows, n_cols = df_work.shape

        if n_cols <= 1 or n_rows <= 1:
            return df_work

        # Determine sample size for statistics and greedy ordering
        if isinstance(early_stop, int) and early_stop > 0:
            max_sample_rows = min(early_stop, 4096)
        else:
            max_sample_rows = 4096

        sample_size = min(n_rows, max_sample_rows)
        if sample_size <= 0:
            return df_work

        # Precompute per-column hashes and average string lengths on the sample
        col_hashes = {}
        col_mean_len = {}

        # Use integer-based indexing for the sample to keep it fast
        sample_idx = df_work.index[:sample_size]

        for col in df_work.columns:
            series_sample = df_work.loc[sample_idx, col]

            # Hash values using pandas' vectorized hashing (fast, C-implemented)
            hashed_series = pd.util.hash_pandas_object(series_sample, index=False)
            hashed_array = hashed_series.to_numpy(dtype="uint64", copy=False)
            col_hashes[col] = hashed_array

            # Estimate average string length for this column
            str_values = series_sample.astype(str)
            lengths = str_values.str.len()
            mean_len = float(lengths.mean())
            # Avoid zero length to keep scoring stable
            if mean_len <= 0.0 or not np.isfinite(mean_len):
                mean_len = 1.0
            col_mean_len[col] = mean_len

        # Greedy ordering based on minimizing distinct combinations of prefixes
        pattern_hash = np.zeros(sample_size, dtype="uint64")
        remaining_cols = list(df_work.columns)
        selected_cols: List[str] = []

        FNV_PRIME = np.uint64(1099511628211)
        OFFSET_BASIS = np.uint64(1469598103934665603)

        # Safe handling of distinct_value_threshold to avoid division by zero
        use_threshold = distinct_value_threshold if distinct_value_threshold > 0 else 0.7

        while remaining_cols:
            best_col = None
            best_score = None

            for col in remaining_cols:
                hashes = col_hashes[col]

                # Combine existing prefix hash with candidate column hashes
                combined = pattern_hash * FNV_PRIME ^ (hashes + OFFSET_BASIS)

                # Count distinct combined hashes
                unique_vals = pd.unique(combined)
                distinct_count = len(unique_vals)
                distinct_ratio = distinct_count / float(sample_size)

                mean_len = col_mean_len[col]

                # Overlap score: reward columns that keep distinct_ratio below threshold
                if use_threshold > 0:
                    stability = max(0.0, use_threshold - distinct_ratio) / use_threshold
                else:
                    stability = max(0.0, 1.0 - distinct_ratio)

                overlap_score = stability * mean_len

                # Small penalty for columns that create many distinct prefixes,
                # also used as a tie-breaker favoring shorter high-distinct columns
                penalty = distinct_ratio * mean_len * 0.001

                score = overlap_score - penalty

                if best_score is None or score > best_score:
                    best_score = score
                    best_col = col

            selected_cols.append(best_col)
            remaining_cols.remove(best_col)

            # Update prefix hash with the best column
            best_hashes = col_hashes[best_col]
            pattern_hash = pattern_hash * FNV_PRIME ^ (best_hashes + OFFSET_BASIS)

        # Reorder DataFrame columns according to selected order
        df_reordered = df_work.loc[:, selected_cols]
        return df_reordered
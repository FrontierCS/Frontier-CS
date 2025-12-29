import pandas as pd
import numpy as np
from typing import List, Any, Optional, Iterable


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
        """
        Reorder columns in the DataFrame to maximize prefix hit rate.
        """
        # Step 1: apply column merges on a copy of the dataframe
        if col_merge:
            df_work = self._apply_column_merges(df, col_merge)
        else:
            df_work = df.copy()

        # Step 2: optimize column order based on heuristic
        if df_work.shape[1] <= 1:
            return df_work

        ordered_cols = self._order_columns(
            df_work,
            early_stop=early_stop,
            distinct_value_threshold=distinct_value_threshold,
        )

        # Step 3: return reordered DataFrame
        return df_work[ordered_cols]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: Optional[Iterable]) -> pd.DataFrame:
        """
        Apply column merges specified in col_merge.
        col_merge: list of groups; each group is iterable of column names or indices.
        """
        if not col_merge:
            return df.copy()

        df_merged = df.copy()
        original_cols = list(df.columns)

        def resolve_col_name(spec: Any) -> Optional[str]:
            # If already a valid column name, return it.
            if isinstance(spec, str) and spec in original_cols:
                return spec
            # Integer index
            if isinstance(spec, int):
                if 0 <= spec < len(original_cols):
                    return original_cols[spec]
                return None
            # String that might be an index
            if isinstance(spec, str):
                if spec.isdigit():
                    idx = int(spec)
                    if 0 <= idx < len(original_cols):
                        return original_cols[idx]
                # non-digit string that may refer to a column not in original_cols -> ignore
                return spec if spec in original_cols else None
            return None

        # Pre-resolve all merge groups to original column names
        resolved_groups: List[List[str]] = []
        for group in col_merge:
            if group is None:
                continue
            # Ensure group is iterable but not a string
            if isinstance(group, (str, bytes)):
                group_iter = [group]
            else:
                try:
                    iter(group)
                    group_iter = list(group)
                except TypeError:
                    group_iter = [group]

            names_raw: List[str] = []
            for spec in group_iter:
                name = resolve_col_name(spec)
                if name is not None:
                    names_raw.append(name)

            # Deduplicate while preserving original column order
            seen = set()
            ordered_names: List[str] = []
            for col in original_cols:
                if col in names_raw and col not in seen:
                    seen.add(col)
                    ordered_names.append(col)

            if ordered_names:
                resolved_groups.append(ordered_names)

        # Apply merges sequentially on df_merged using resolved names
        for group_cols in resolved_groups:
            # Keep only columns that are still present (earlier merges may drop some)
            existing_cols = [c for c in group_cols if c in df_merged.columns]
            if len(existing_cols) <= 1:
                # Nothing to merge or single-column merge (no-op)
                continue

            new_name = "MERGED_" + "_".join(existing_cols)
            # Concatenate string representation of each column in the group
            df_merged[new_name] = df_merged[existing_cols].astype(str).agg("".join, axis=1)
            # Drop original columns
            df_merged.drop(columns=existing_cols, inplace=True)

        return df_merged

    def _order_columns(
        self,
        df: pd.DataFrame,
        early_stop: int = 100000,
        distinct_value_threshold: float = 0.7,
    ) -> List[Any]:
        """
        Compute a heuristic ordering of columns to maximize expected prefix LCP.
        """
        n_rows = len(df)
        if n_rows == 0:
            return list(df.columns)

        # Limit number of rows used for statistics by early_stop
        sample_n = min(n_rows, early_stop)
        df_sample = df.iloc[:sample_n]

        # Convert to strings once for all metrics
        df_str = df_sample.astype(str)
        n_sample = len(df_str)

        col_scores = {}

        for col in df_str.columns:
            s = df_str[col]

            if n_sample == 0:
                avg_len = 0.0
                p_eq = 0.0
                distinct_ratio = 1.0
            else:
                # Average string length
                lens = s.str.len()
                avg_len = float(lens.mean())

                # Frequency distribution for probability two random rows share the same value
                vc = s.value_counts(dropna=False)
                counts = vc.values.astype(np.float64)
                freqs = counts / float(n_sample)
                p_eq = float(np.dot(freqs, freqs))  # sum p_i^2
                distinct_ratio = float(len(vc)) / float(n_sample)

            # Clip p_eq to avoid division by zero
            p_clipped = max(min(p_eq, 1.0 - 1e-9), 0.0)

            # Heuristic core: emphasize columns with high equality probability and long length
            # score ~ L * p^2 / (1 - p)
            core = (p_clipped * p_clipped) / (1.0 - p_clipped + 1e-9) if n_sample > 0 else 0.0
            score = avg_len * core

            # Penalize very high-cardinality columns
            if distinct_ratio > distinct_value_threshold:
                score *= 0.2

            # Additional penalty for likely identifier columns based on name
            col_name_str = str(col).lower()
            if (
                col_name_str == "id"
                or col_name_str.endswith("_id")
                or col_name_str.startswith("id_")
                or col_name_str == "index"
                or col_name_str.endswith("id") and len(col_name_str) <= 5
                or "uuid" in col_name_str
                or "guid" in col_name_str
            ):
                score *= 0.05

            col_scores[col] = (score, p_eq, avg_len, distinct_ratio)

        # Sort columns by descending score; break ties by original order implicitly
        ordered_cols = sorted(
            df.columns,
            key=lambda c: col_scores.get(c, (0.0, 0.0, 0.0, 1.0))[0],
            reverse=True,
        )
        return ordered_cols
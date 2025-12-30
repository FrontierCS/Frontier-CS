import pandas as pd
from typing import List, Optional
import numpy as np

class Solution:
    def solve(
        self,
        df: pd.DataFrame,
        early_stop: int = 100000,
        row_stop: int = 4,
        col_stop: int = 2,
        col_merge: Optional[List] = None,
        one_way_dep: Optional[List] = None,
        distinct_value_threshold: float = 0.7,
        parallel: bool = True,
    ) -> pd.DataFrame:
        # Work on a copy to avoid modifying the original
        df = df.copy()

        # 1. Apply column merges if specified
        if col_merge:
            merged_cols = []
            for i, group in enumerate(col_merge):
                # Ensure all columns in the group exist
                valid_cols = [c for c in group if c in df.columns]
                if not valid_cols:
                    continue
                # Create merged column by concatenating values as strings
                merged_name = f"__merged_{i}"
                df[merged_name] = df[valid_cols].astype(str).agg(''.join, axis=1)
                # Drop original columns
                df.drop(columns=valid_cols, inplace=True)
                merged_cols.append(merged_name)

        # 2. Convert all remaining columns to strings
        df = df.astype(str)

        # 3. Greedy column ordering to minimize distinct prefixes
        cols = list(df.columns)
        n_rows = len(df)
        # Precompute column data as lists for faster access
        col_data = {c: df[c].tolist() for c in cols}
        # Current prefix strings for each row
        current = [''] * n_rows
        ordered = []

        while cols:
            best_col = None
            best_distinct = float('inf')
            best_total_len = 0

            # Evaluate each candidate column
            for c in cols:
                # Build new strings by concatenating current prefix with column values
                new_strings = [current[i] + col_data[c][i] for i in range(n_rows)]
                distinct = len(set(new_strings))
                total_len = sum(len(s) for s in new_strings)
                # Select column that gives the fewest distinct strings;
                # tie-break by larger total length (favors longer common prefixes)
                if (distinct < best_distinct or
                    (distinct == best_distinct and total_len > best_total_len)):
                    best_distinct = distinct
                    best_total_len = total_len
                    best_col = c

            # Append the best column to the order
            ordered.append(best_col)
            # Update current prefixes
            current = [current[i] + col_data[best_col][i] for i in range(n_rows)]
            cols.remove(best_col)

        # Return DataFrame with columns in the determined order
        return df[ordered]
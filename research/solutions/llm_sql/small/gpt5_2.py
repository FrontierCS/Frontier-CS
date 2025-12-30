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
        # Work on a copy to avoid modifying the original DataFrame
        df_out = df.copy()

        # Helper to convert merge specs (names or indices) to existing column names
        def resolve_group_to_names(group, original_cols):
            names = []
            for item in group:
                if isinstance(item, int):
                    if 0 <= item < len(original_cols):
                        names.append(original_cols[item])
                else:
                    # assume string-like column name
                    if item in original_cols:
                        names.append(item)
            # keep order as given
            return names

        # Apply merges before reordering
        if col_merge:
            # Keep a reference to the original columns for index-based mapping
            original_cols = list(df.columns)
            used_cols = set()
            for group in col_merge:
                if not isinstance(group, (list, tuple)):
                    continue
                group_names = resolve_group_to_names(group, original_cols)
                # Filter out columns that are already merged/dropped
                group_names = [c for c in group_names if c in df_out.columns and c not in used_cols]
                if len(group_names) <= 1:
                    # No effective merge
                    continue
                # Determine insertion position as the smallest index among group cols
                positions = [df_out.columns.get_loc(c) for c in group_names]
                insert_pos = min(positions)
                # Create merged column values by concatenating as strings without separator
                merged_values = df_out[group_names].astype(str).agg(''.join, axis=1)
                # New column name
                new_col_name = "MERGED_" + "|".join(group_names)
                # Insert new column
                df_out.insert(loc=insert_pos, column=new_col_name, value=merged_values)
                # Drop old columns
                df_out.drop(columns=group_names, inplace=True)
                # Mark these columns as used
                for c in group_names:
                    used_cols.add(c)

        # Compute statistics for ordering
        cols = list(df_out.columns)
        N = len(df_out)
        metrics = []
        eps = 1e-12

        for c in cols:
            s = df_out[c]
            # Convert to string for analysis without modifying df_out permanently
            str_s = s.astype(str)
            lengths = str_s.str.len()
            L_mean = float(lengths.mean()) if N > 0 else 0.0
            # Value distribution (probabilities)
            vc = str_s.value_counts(dropna=False)
            counts = vc.values.astype(np.float64)
            if counts.size == 0:
                g = 0.0
            else:
                probs = counts / N
                g = float(np.sum(probs * probs))  # sum p^2, in (1/N, 1]
            g = max(min(g, 1.0), 1.0 / max(N, 1))  # clamp for numerical stability
            # tau = (1/g - 1) / L
            denom = L_mean if L_mean > eps else eps
            tau = (1.0 / g - 1.0) / denom
            metrics.append((c, tau, -L_mean, -g))  # store tie-breakers: prefer larger L, larger g

        # Sort columns by ascending tau, then by larger L, then by larger g (due to negative values)
        metrics.sort(key=lambda x: (x[1], x[2], x[3]))
        sorted_cols = [m[0] for m in metrics]

        # Return DataFrame with reordered columns
        return df_out.loc[:, sorted_cols]
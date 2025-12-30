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
        """
        Reorder columns in the DataFrame to maximize prefix hit rate.
        
        Strategy:
        1. Apply column merges as specified.
        2. Sort columns based on a heuristic: minimize (Entropy / Length).
           We approximate Entropy using log(nunique).
           Columns with high cardinality (near unique IDs) are moved to the end
           as they break the common prefix for all subsequent columns.
           
        Heuristic Score = log(nunique) / mean_length
        - Low nunique (high repetition) -> Low score -> Placed earlier.
        - High length (covers more distance) -> Low score -> Placed earlier.
        """
        
        # Work on a copy to avoid side effects
        df_curr = df.copy()
        
        # 1. Apply Column Merges
        # Merges are applied before reordering.
        if col_merge:
            for group in col_merge:
                # Filter group columns that exist in the DataFrame
                valid_group = [c for c in group if c in df_curr.columns]
                
                if not valid_group:
                    continue
                
                # If only one column, nothing to merge, but we keep the logic consistent
                # Create new column name (concatenation of old names)
                new_col_name = "".join(valid_group)
                
                # If the new name conflicts with an existing column not in the group, 
                # we might have an issue, but we assume standard inputs.
                # If valid_group has 1 item and name is same, it's a no-op.
                if len(valid_group) == 1 and new_col_name == valid_group[0]:
                    continue

                # Concatenate string representations of the columns
                # We start with the first column
                combined_series = df_curr[valid_group[0]].astype(str)
                for col in valid_group[1:]:
                    combined_series = combined_series + df_curr[col].astype(str)
                
                # Assign new column
                df_curr[new_col_name] = combined_series
                
                # Drop original columns. 
                # Note: If new_col_name was one of the original names (e.g. self-merge?),
                # we should be careful. But drop takes list.
                # To be safe, drop valid_group columns, but ensure we don't drop the new one if names overlap.
                cols_to_drop = [c for c in valid_group if c != new_col_name]
                if cols_to_drop:
                    df_curr.drop(columns=cols_to_drop, inplace=True)

        # 2. Calculate Stats for Heuristic
        # We process all columns currently in the dataframe
        columns = df_curr.columns.tolist()
        N = len(df_curr)
        stats = []
        
        # Threshold for considering a column as "High Cardinality" (effectively an ID)
        threshold_count = distinct_value_threshold * N
        
        for col in columns:
            series = df_curr[col]
            # Convert to string once
            str_series = series.astype(str)
            
            # 1. Cardinality (Number of unique values)
            # We count including NaNs (which become 'nan' string)
            n_unique = str_series.nunique()
            
            # 2. Mean Length
            # Length of the string representation
            mean_len = str_series.str.len().mean()
            
            stats.append((col, n_unique, mean_len))
        
        # 3. Sort Columns
        low_card_cols = []
        high_card_cols = []
        
        for col, nu, ml in stats:
            # Avoid division by zero for empty strings
            safe_ml = ml if ml > 0 else 0.001
            
            # Heuristic: log(nunique) / mean_length
            # We want small nunique (low cost) and large mean_length (high value)
            # Ratio: Cost / Value. We sort Ascending (Lowest cost/value first).
            # log(1) is 0. 
            val = math.log(nu) if nu > 0 else 0
            score = val / safe_ml
            
            # Partition based on cardinality threshold
            if nu > threshold_count:
                # High cardinality columns go to the end
                high_card_cols.append((score, col))
            else:
                low_card_cols.append((score, col))
        
        # Sort both groups by the heuristic score
        low_card_cols.sort(key=lambda x: x[0])
        high_card_cols.sort(key=lambda x: x[0])
        
        # Concatenate: Low Cardinality first, then High Cardinality
        final_order = [x[1] for x in low_card_cols] + [x[1] for x in high_card_cols]
        
        return df_curr[final_order]
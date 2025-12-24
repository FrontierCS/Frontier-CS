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
        # Work on a copy of the dataframe
        df_out = df.copy()
        
        # 1. Apply Column Merges
        if col_merge:
            for group in col_merge:
                # Filter to columns that exist in the current dataframe
                valid_group = [c for c in group if c in df_out.columns]
                
                # We need at least 2 columns to merge
                if len(valid_group) > 1:
                    # Construct new column name
                    new_col_name = "_".join(map(str, valid_group))
                    
                    # Concatenate the string representations of the columns
                    # Initialize with the first column
                    combined = df_out[valid_group[0]].astype(str)
                    
                    # Add subsequent columns
                    for col in valid_group[1:]:
                        combined = combined + df_out[col].astype(str)
                    
                    # Assign the new merged column
                    df_out[new_col_name] = combined
                    
                    # Remove the original columns
                    df_out.drop(columns=valid_group, inplace=True)
        
        # 2. Compute Column Statistics
        # We want to order columns to maximize the expected length of the common prefix.
        # We use a greedy heuristic based on Smith's rule for scheduling: (p * L) / (1 - p)
        # p: collision probability (sum of squared frequencies)
        # L: average string length
        # Higher score -> Earlier position
        
        col_stats = []
        
        for col in df_out.columns:
            # Convert to string to calculate length and probability statistics
            s_str = df_out[col].astype(str)
            
            # Calculate Average Length (L)
            avg_len = s_str.str.len().mean()
            
            # Calculate Collision Probability (p)
            # This is the probability that two randomly selected rows share the same value
            freqs = s_str.value_counts(normalize=True)
            p = (freqs * freqs).sum()
            
            # Calculate Score
            # If p is 1.0 (constant column), score is infinite (highest priority)
            if p >= 0.9999999:
                score = float('inf')
            else:
                score = (p * avg_len) / (1.0 - p)
            
            col_stats.append((score, avg_len, col))
            
        # 3. Sort Columns
        # Primary sort key: Score (descending)
        # Secondary sort key: Average Length (descending) - prefers longer matches for same probability
        col_stats.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        # Extract the ordered column names
        new_column_order = [item[2] for item in col_stats]
        
        # Return the DataFrame with reordered columns
        return df_out[new_column_order]

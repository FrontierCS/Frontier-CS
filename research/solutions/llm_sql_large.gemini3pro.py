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
        """
        Reorder columns in the DataFrame to maximize prefix hit rate.
        """
        # Create a working copy to avoid modifying the original dataframe in place
        df = df.copy()

        # 1. Apply Column Merges
        # Columns in each merge group are concatenated into a single column
        # The merged column replaces the original columns
        if col_merge:
            for group in col_merge:
                # Identify columns from the group that exist in the dataframe
                valid_cols = [c for c in group if c in df.columns]
                
                if not valid_cols:
                    continue
                
                # Perform vectorized string concatenation
                # Convert first column to string
                merged_series = df[valid_cols[0]].astype(str)
                
                # Concatenate subsequent columns
                for col in valid_cols[1:]:
                    merged_series = merged_series + df[col].astype(str)
                
                # Construct new column name
                new_col_name = "".join(valid_cols)
                
                # Remove original columns
                df.drop(columns=valid_cols, inplace=True)
                
                # Add the new merged column
                df[new_col_name] = merged_series

        # 2. Prepare for Metric Calculation
        # Convert all data to string format once to ensure consistent length/value calculations
        # Using astype(str) handles NaNs and various types uniformly
        df_str = df.astype(str)
        
        column_metrics = []

        # 3. Calculate Metrics for each column
        # We calculate:
        # - CP (Collision Probability): Sum of squared probabilities of each unique value.
        #   Represents the probability that two random rows share the same value for this column.
        # - MeanLen: Weighted average length of the string values.
        
        for col in df_str.columns:
            series = df_str[col]
            
            # Get value counts normalized (probabilities)
            vc = series.value_counts(normalize=True)
            
            # CP calculation
            # High CP means low cardinality / high redundancy (good for prefix matching)
            cp = (vc * vc).sum()
            
            # Mean Length calculation
            # vc.index contains the unique string values
            # vc contains the probabilities
            # Average length = Sum(len(val) * prob(val))
            mean_len = (vc.index.str.len() * vc).sum()
            
            column_metrics.append({
                'col': col,
                'cp': cp,
                'mean_len': mean_len
            })

        # 4. Compute Heuristic Score and Sort
        # Heuristic: Score = (MeanLen * CP) / (1 - CP)
        # We want high probability columns first to maximize the depth of the common prefix trie.
        # If probabilities are similar, longer columns provide more gain.
        # As CP -> 1 (constant column), Score -> Infinity.
        
        for metric in column_metrics:
            cp = metric['cp']
            mean_len = metric['mean_len']
            
            # Handle numerical stability for constant columns
            if cp >= 0.999999:
                score = float('inf')
            else:
                score = (mean_len * cp) / (1.0 - cp)
            
            metric['score'] = score

        # Sort columns by score descending
        column_metrics.sort(key=lambda x: x['score'], reverse=True)
        
        # 5. Reconstruct DataFrame with new column order
        sorted_cols = [x['col'] for x in column_metrics]
        
        return df[sorted_cols]
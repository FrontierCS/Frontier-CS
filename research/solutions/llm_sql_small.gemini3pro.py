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
        
        # Working copy
        df_curr = df.copy()
        
        # 1. Convert all columns to string
        for col in df_curr.columns:
            df_curr[col] = df_curr[col].astype(str)
            
        # 2. Apply Column Merges
        if col_merge:
            for group in col_merge:
                # Filter columns that exist in the dataframe
                valid_group = [c for c in group if c in df_curr.columns]
                if not valid_group:
                    continue
                
                # Generate new column name
                new_col_name = "_".join(valid_group)
                # Handle name collision if necessary
                while new_col_name in df_curr.columns and new_col_name not in valid_group:
                     new_col_name = "merged_" + new_col_name

                # Concatenate string values
                merged_series = df_curr[valid_group[0]]
                for c in valid_group[1:]:
                    merged_series = merged_series + df_curr[c]
                
                df_curr[new_col_name] = merged_series
                df_curr.drop(columns=valid_group, inplace=True)
        
        cols = list(df_curr.columns)
        if not cols:
            return df_curr

        # 3. Calculate Column Statistics for Heuristic
        # Heuristic: Score = (Collision Probability) * (Mean Length)
        # Collision Prob = Sum(freq^2)
        
        col_stats = {}
        col_means = {}
        
        for c in cols:
            # Value counts normalize=True gives probabilities
            vc = df_curr[c].value_counts(normalize=True)
            # Sum of squares of probabilities
            cp = np.sum(vc.values ** 2)
            
            # Mean length of string representation
            mean_len = df_curr[c].str.len().mean()
            col_means[c] = mean_len
            
            # Score
            col_stats[c] = cp * mean_len
            
        # Initial Sort by Heuristic (Descending)
        current_perm = sorted(cols, key=lambda c: col_stats[c], reverse=True)
        
        # 4. Hill Climbing Optimization
        # Proxy metric: Sum of LCPs of adjacent rows in sorted order.
        # This approximates the clusterability of the dataset given the column order.
        
        # Use a sample for speed if N is large to ensure runtime constraints
        sample_n = 10000 
        if len(df_curr) > sample_n:
            df_eval = df_curr.sample(n=sample_n, random_state=42)
        else:
            df_eval = df_curr
            
        def evaluate(perm):
            # Sort by current permutation
            df_sorted = df_eval.sort_values(by=perm)
            
            # Convert to numpy for comparison
            mat = df_sorted[perm].to_numpy()
            
            # Compare adjacent rows: (N-1, M) boolean matrix
            if len(mat) < 2:
                return 0
            eq = (mat[1:] == mat[:-1])
            
            # Compute cumulative prefix match (logical AND scan)
            # Use minimum.accumulate for boolean cumulative AND
            eq_cum = np.minimum.accumulate(eq, axis=1)
            
            # Weighted sum by column lengths
            means_vec = np.array([col_means[c] for c in perm])
            
            # Sum score
            score = np.sum(eq_cum @ means_vec)
            return score

        # Initial Score
        current_score = evaluate(current_perm)
        
        # Hill Climbing: Try swapping adjacent columns
        # Limit passes to ensure runtime constraint
        passes = 2
        improved = True
        
        while passes > 0 and improved:
            improved = False
            passes -= 1
            
            for i in range(len(current_perm) - 1):
                # Create candidate by swapping
                cand = current_perm[:]
                cand[i], cand[i+1] = cand[i+1], cand[i]
                
                # Evaluate
                cand_score = evaluate(cand)
                
                if cand_score > current_score:
                    current_score = cand_score
                    current_perm = cand
                    improved = True
        
        # Return DataFrame with reordered columns
        return df_curr[current_perm]

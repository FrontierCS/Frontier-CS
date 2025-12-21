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
        # Work on a copy to prevent modifying the original dataframe
        df_curr = df.copy()
        N = len(df_curr)
        if N == 0:
            return df_curr

        # 1. Apply Column Merges
        # Merge groups of columns into single columns by concatenation
        if col_merge:
            for group in col_merge:
                valid_cols = [c for c in group if c in df_curr.columns]
                if not valid_cols:
                    continue
                
                # Vectorized string concatenation of the columns
                merged_series = df_curr[valid_cols[0]].astype(str)
                for c in valid_cols[1:]:
                    merged_series = merged_series + df_curr[c].astype(str)
                
                # Name the new column using joined names of original columns
                new_col_name = "|".join(map(str, valid_cols))
                df_curr[new_col_name] = merged_series
                
                # Remove the original columns
                df_curr.drop(columns=valid_cols, inplace=True)

        # 2. Calculate Heuristic Scores
        # We want to maximize the expected prefix match length.
        # This is modeled as a scheduling problem (Smith's Rule).
        # We sort columns by Score = (P * L) / (1 - P), where:
        #   P = Probability of a match (approximated by sum of squared probabilities of values)
        #   L = Expected length of the column value given a match
        
        cols = list(df_curr.columns)
        scores = []
        inv_N = 1.0 / N
        inv_N_sq = inv_N * inv_N
        
        for col in cols:
            # Convert to string for length and frequency analysis
            series = df_curr[col].astype(str)
            
            # Calculate value counts
            vc = series.value_counts()
            counts = vc.values
            
            # Calculate squared probabilities: (count / N)^2
            probs_sq = (counts * counts) * inv_N_sq
            
            # P: Probability of match
            P = np.sum(probs_sq)
            
            # PL: Expected length contribution (weighted by match probability)
            # lengths aligned with counts in vc
            lengths = vc.index.map(len).values
            PL = np.sum(probs_sq * lengths)
            
            # Calculate score
            # Prioritize constant columns (P approx 1) infinitely high
            if P > 0.99999999:
                s = float('inf')
            else:
                s = PL / (1.0 - P)
            
            scores.append((s, col))
        
        # 3. Sort and Reorder
        # Descending order of scores
        scores.sort(key=lambda x: x[0], reverse=True)
        ordered_cols = [x[1] for x in scores]
        
        return df_curr[ordered_cols]

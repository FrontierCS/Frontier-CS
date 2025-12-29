import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

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
        1. Apply column merges.
        2. Sort columns based on heuristics:
           - Primary: Cardinality (Ascending). Low cardinality minimizes branching in the prefix tree.
           - Secondary: Collision Score (Descending). Higher concentration (skew) preserves larger groups.
           - Tertiary: Average Length (Descending). Longer strings contribute more to LCP score.
        """
        
        # Work on a copy to avoid modifying the input inplace unexpectedly
        df_res = df.copy()
        
        # 1. Apply Column Merges
        if col_merge:
            for group in col_merge:
                # Identify valid columns in this group that exist in current dataframe
                valid_cols = [c for c in group if c in df_res.columns]
                
                # Need at least 1 column to process
                if not valid_cols:
                    continue
                
                # Concatenate columns as strings
                # Start with first column
                merged_series = df_res[valid_cols[0]].astype(str)
                for c in valid_cols[1:]:
                    merged_series = merged_series + df_res[c].astype(str)
                
                # Generate new column name. Use concatenation of names to ensure uniqueness.
                new_col_name = "".join([str(c) for c in valid_cols])
                
                # Handle potential name collision
                if new_col_name in df_res.columns and new_col_name not in valid_cols:
                    base_name = new_col_name
                    suffix = 1
                    while new_col_name in df_res.columns:
                        new_col_name = f"{base_name}_{suffix}"
                        suffix += 1
                
                # Assign merged series
                df_res[new_col_name] = merged_series
                
                # Drop original columns (excluding the new one if it overwrites)
                cols_to_drop = [c for c in valid_cols if c != new_col_name]
                if cols_to_drop:
                    df_res.drop(columns=cols_to_drop, inplace=True)

        # 2. Calculate Metrics for Sorting
        cols = list(df_res.columns)
        
        def get_col_metric(col_name):
            # Metrics must be based on string representation
            s = df_res[col_name].astype(str)
            N = len(s)
            
            if N == 0:
                return (col_name, 0, 0.0, 0.0)
            
            # Value counts
            vc = s.value_counts(normalize=False, sort=False)
            counts = vc.values
            probs = counts / N
            
            # Metric 1: Cardinality (Ascending)
            # Fewer unique values means we split the dataset into fewer groups,
            # keeping more rows together for subsequent matches.
            card = len(vc)
            
            # Metric 2: Collision Score (Descending)
            # sum(p^2). Higher score means the distribution is more skewed (e.g. 90/10 vs 50/50).
            # A more skewed distribution preserves a larger main group.
            coll_score = np.sum(probs * probs)
            
            # Metric 3: Weighted Average Length (Descending)
            # If structural properties are similar, prefer longer strings to boost LCP.
            lengths = vc.index.astype(str).str.len().values
            avg_len = np.sum(probs * lengths)
            
            return (col_name, card, coll_score, avg_len)

        # Compute metrics
        # Use parallel processing if efficient
        if parallel and len(cols) > 10:
            with ThreadPoolExecutor(max_workers=8) as executor:
                metrics = list(executor.map(get_col_metric, cols))
        else:
            metrics = [get_col_metric(c) for c in cols]
        
        # 3. Sort Columns
        # Sort key: (Cardinality ASC, Collision Score DESC, Avg Length DESC)
        metrics.sort(key=lambda x: (x[1], -x[2], -x[3]))
        
        sorted_cols = [x[0] for x in metrics]
        
        return df_res[sorted_cols]
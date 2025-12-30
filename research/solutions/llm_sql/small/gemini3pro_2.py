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
        # Create a working copy
        df_curr = df.copy()
        
        # 1. Apply Column Merges
        if col_merge:
            for group in col_merge:
                # Filter columns that are actually in the dataframe
                valid_group = [c for c in group if c in df_curr.columns]
                if len(valid_group) > 1:
                    # Construct merged column values
                    merged_series = df_curr[valid_group[0]].astype(str)
                    for c in valid_group[1:]:
                        merged_series = merged_series + df_curr[c].astype(str)
                    
                    # Create new column name
                    new_col = "|".join(valid_group)
                    
                    # Assign new column
                    df_curr[new_col] = merged_series
                    
                    # Drop original columns
                    df_curr = df_curr.drop(columns=valid_group)
        
        # 2. Preprocess columns
        cols = list(df_curr.columns)
        n_rows = len(df_curr)
        
        if n_rows == 0 or not cols:
            return df_curr
            
        # Precompute integer codes and string lengths
        col_codes = {}
        col_lengths = {}
        
        for c in cols:
            vals = df_curr[c].astype(str).values
            codes, uniques = pd.factorize(vals, sort=False)
            unique_lens = np.array([len(s) for s in uniques])
            col_codes[c] = codes
            col_lengths[c] = unique_lens[codes]
            
        # 3. Greedy Optimization
        remaining_cols = set(cols)
        ordered_cols = []
        
        # Initial partition contains all row indices [0, ..., N-1]
        partitions = [np.arange(n_rows)]
        
        while remaining_cols:
            best_col = None
            max_score = -1
            
            # If partitions are all singletons, order doesn't matter for the metric
            if not partitions:
                ordered_cols.extend(sorted(list(remaining_cols)))
                break
            
            candidates = sorted(list(remaining_cols))
            
            for col in candidates:
                current_score = 0
                c_codes = col_codes[col]
                c_lens = col_lengths[col]
                
                # Evaluate score across all current partitions
                for indices in partitions:
                    if len(indices) < 2:
                        continue
                        
                    subset_codes = c_codes[indices]
                    subset_lens = c_lens[indices]
                    
                    # Find first occurrences of each code in this partition
                    # indices are sorted by row index, so first occurrence corresponds to earliest row j
                    _, first_indices = np.unique(subset_codes, return_index=True)
                    
                    # Score is total length minus length of first occurrences
                    # (Only subsequent occurrences contribute to LCP with a predecessor)
                    total_len = np.sum(subset_lens)
                    first_len = np.sum(subset_lens[first_indices])
                    current_score += (total_len - first_len)
                
                if current_score > max_score:
                    max_score = current_score
                    best_col = col
            
            # If we didn't find a column (should not happen unless empty), pick first
            if best_col is None:
                best_col = candidates[0]
                
            ordered_cols.append(best_col)
            remaining_cols.remove(best_col)
            
            # Update partitions based on the chosen column
            new_partitions = []
            b_codes = col_codes[best_col]
            
            for indices in partitions:
                if len(indices) < 2:
                    continue
                
                subset_codes = b_codes[indices]
                
                # Stable sort by code to group identical values while preserving time order
                sort_idx = np.argsort(subset_codes, kind='stable')
                sorted_codes = subset_codes[sort_idx]
                sorted_indices = indices[sort_idx]
                
                # Split where codes change
                split_indices = np.flatnonzero(sorted_codes[1:] != sorted_codes[:-1]) + 1
                
                if len(split_indices) > 0:
                    sub_groups = np.split(sorted_indices, split_indices)
                    for grp in sub_groups:
                        if len(grp) > 1:
                            new_partitions.append(grp)
                else:
                    new_partitions.append(sorted_indices)
            
            partitions = new_partitions
            
        return df_curr[ordered_cols]
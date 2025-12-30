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
        # Convert all data to string to ensure consistent concatenation and length calculations
        df_process = df.astype(str)
        
        # 1. Apply Column Merges
        if col_merge:
            for group in col_merge:
                # Identify columns from the group that are present in the dataframe
                valid_group = [c for c in group if c in df_process.columns]
                if not valid_group:
                    continue
                
                # Create the merged column name
                new_col_name = "_".join(valid_group)
                while new_col_name in df_process.columns and new_col_name not in valid_group:
                    new_col_name += "_"
                
                # Concatenate the string values
                new_series = df_process[valid_group[0]]
                for c in valid_group[1:]:
                    new_series = new_series + df_process[c]
                
                df_process[new_col_name] = new_series
                
                # Drop the original columns
                df_process.drop(columns=valid_group, inplace=True)
        
        # 2. Precompute Statistics for Heuristic and Greedy Search
        cols = list(df_process.columns)
        n_rows = len(df_process)
        
        # Calculate length of string representation for each cell
        col_lengths = {c: df_process[c].str.len().values for c in cols}
        
        # Calculate heuristics: unique count and average length
        col_stats = {}
        for c in cols:
            nunique = df_process[c].nunique()
            mean_len = np.mean(col_lengths[c])
            col_stats[c] = (nunique, mean_len)
            
        # Sort candidates by heuristic: Primary = nunique (asc), Secondary = mean_len (desc)
        sorted_candidates = sorted(cols, key=lambda c: (col_stats[c][0], -col_stats[c][1]))
        
        # 3. Greedy Optimization Loop
        ordered_cols = []
        remaining_cols = set(cols)
        
        # Track groups of rows that share the same prefix so far
        group_ids = np.zeros(n_rows, dtype=np.int32)
        
        # Limit the number of candidates evaluated per step for performance
        CANDIDATE_LIMIT = 15
        
        for _ in range(len(cols)):
            if not remaining_cols:
                break
                
            # If every row is in its own unique group, no further prefix matches are possible.
            if group_ids.max() == n_rows - 1:
                remaining_sorted = [c for c in sorted_candidates if c in remaining_cols]
                ordered_cols.extend(remaining_sorted)
                break
            
            # Select top candidates to evaluate
            candidates = []
            count = 0
            for c in sorted_candidates:
                if c in remaining_cols:
                    candidates.append(c)
                    count += 1
                    if count >= CANDIDATE_LIMIT:
                        break
            
            best_col = None
            max_gain = -1.0
            
            # Prepare a temporary DataFrame for duplicate checking
            check_df = pd.DataFrame({'g': group_ids})
            
            for c in candidates:
                check_df['v'] = df_process[c]
                
                # Check for duplicates (matches with previous rows in the same group)
                is_dup = check_df.duplicated(subset=['g', 'v'], keep='first')
                
                if not is_dup.any():
                    gain = 0.0
                else:
                    gain = np.sum(col_lengths[c][is_dup])
                
                if gain > max_gain:
                    max_gain = gain
                    best_col = c
            
            if best_col is None:
                best_col = candidates[0]
            
            ordered_cols.append(best_col)
            remaining_cols.remove(best_col)
            
            # Update groups for the next iteration
            if remaining_cols:
                check_df['v'] = df_process[best_col]
                group_ids = check_df.groupby(['g', 'v'], sort=False).ngroup().values
        
        return df_process[ordered_cols]
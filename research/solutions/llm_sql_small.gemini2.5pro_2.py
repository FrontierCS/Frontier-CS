import pandas as pd
import numpy as np
from joblib import Parallel, delayed

class Solution:

    @staticmethod
    def _calculate_total_lcp_trie(prefixes: np.ndarray) -> int:
        """
        Calculates the sum of Longest Common Prefixes (LCPs) for a list of strings
        using a Trie. This efficiently computes sum_{i} max_{j<i} LCP(s_i, s_j).
        """
        root = {}
        total_lcp = 0
        for s in prefixes:
            node = root
            lcp = 0
            path_exists = True
            for char in s:
                if path_exists and char in node:
                    node = node[char]
                    lcp += 1
                else:
                    if path_exists:
                        path_exists = False
                    node[char] = {}
                    node = node[char]
            total_lcp += lcp
        return total_lcp

    @staticmethod
    def _calculate_lcp_score(current_prefixes: np.ndarray, new_column_data: np.ndarray) -> int:
        """
        Helper function to calculate the LCP score if a new column is appended.
        Designed for parallel execution.
        """
        trial_prefixes = np.core.defchararray.add(current_prefixes, new_column_data)
        return Solution._calculate_total_lcp_trie(trial_prefixes)

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
        
        if col_merge:
            df_processed = df.copy()
            cols_to_drop = set()
            new_cols_dict = {}
            for group in col_merge:
                if not isinstance(group, list):
                    continue
                valid_group = [c for c in group if c in df_processed.columns]
                if len(valid_group) < 2:
                    continue
                
                merged_col_name = '_'.join(valid_group)
                new_cols_dict[merged_col_name] = df_processed[valid_group].astype(str).agg(''.join, axis=1)
                cols_to_drop.update(valid_group)
            
            if cols_to_drop:
                df_processed.drop(columns=list(cols_to_drop), inplace=True)
                for name, data in new_cols_dict.items():
                    df_processed[name] = data
        else:
            df_processed = df

        if df_processed.shape[1] <= 1:
            return df_processed

        sample_size = min(len(df_processed), 5000)
        if sample_size == 0:
            return df_processed
            
        sample_df = df_processed.head(sample_size)
        str_array = sample_df.astype(str).to_numpy()
        
        num_rows, num_cols = str_array.shape
        original_cols = sample_df.columns.tolist()

        perm_indices = []
        remaining_indices = list(range(num_cols))
        
        current_prefixes = np.array([''] * num_rows, dtype=object)
        
        for _ in range(num_cols):
            if not remaining_indices:
                break

            if parallel:
                scores = Parallel(n_jobs=-1, prefer="threads")(
                    delayed(self._calculate_lcp_score)(current_prefixes, str_array[:, col_idx])
                    for col_idx in remaining_indices
                )
            else:
                scores = [
                    self._calculate_lcp_score(current_prefixes, str_array[:, col_idx])
                    for col_idx in remaining_indices
                ]
            
            best_score_idx_in_rem = np.argmax(scores)
            best_col_idx = remaining_indices.pop(best_score_idx_in_rem)
            
            perm_indices.append(best_col_idx)
            current_prefixes = np.core.defchararray.add(current_prefixes, str_array[:, best_col_idx])
            
        final_col_order = [original_cols[i] for i in perm_indices]
        
        return df_processed[final_col_order]
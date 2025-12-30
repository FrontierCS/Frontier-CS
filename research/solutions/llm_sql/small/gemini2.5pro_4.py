import pandas as pd
import numpy as np
from joblib import Parallel, delayed

def _calculate_distinct_count(cols, df_str_data):
    """
    Calculates the number of unique rows for a subset of columns.
    A helper function for parallel processing, defined at the top level.
    """
    if not cols:
        return 1
    return df_str_data[cols].drop_duplicates().shape[0]

class Solution:
    """
    Implements the solution for reordering CSV columns to maximize KV-cache hit rate.
    """
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
        Reorders columns in the DataFrame to maximize prefix hit rate.

        The strategy is as follows:
        1.  Handle column merges as specified.
        2.  Partition columns into low-cardinality and high-cardinality groups. This is
            because low-cardinality columns are better for creating common prefixes.
        3.  For low-cardinality columns, use a greedy forward selection algorithm to find
            an optimal ordering. At each step, add the column that results in the minimum
            increase in the number of unique prefixes. This process is parallelized for
            efficiency.
        4.  For high-cardinality columns, which are likely to break prefixes, place them
            at the end. They are ordered among themselves by their cardinality.
        5.  Combine the ordered low and high cardinality columns to get the final order.
        """
        # Step 1: Handle column merges
        if col_merge:
            work_df = df.copy()
            
            all_merged_cols = set()
            for group in col_merge:
                for col in group:
                    if col in work_df.columns:
                        all_merged_cols.add(col)

            unmerged_cols_df = work_df.drop(columns=list(all_merged_cols), errors='ignore')
            
            merged_components = [unmerged_cols_df]
            for i, group in enumerate(col_merge):
                valid_group = [c for c in group if c in work_df.columns]
                if not valid_group:
                    continue
                
                new_col_name = f"__merged_{'_'.join(sorted(valid_group))}"
                merged_col = work_df[valid_group].astype(str).agg(''.join, axis=1).rename(new_col_name)
                merged_components.append(merged_col)
                
            work_df = pd.concat(merged_components, axis=1)
        else:
            work_df = df

        candidate_cols = list(work_df.columns)
        num_cols = len(candidate_cols)
        
        if num_cols <= 1:
            return work_df

        df_str = work_df.astype(str)
        n_rows = len(df_str)

        # Step 2: Partition columns into low and high cardinality
        high_card_cols = []
        low_card_cols = []
        
        if n_rows > 0:
            sample_size = min(n_rows, 5000)
            df_sample = df_str.head(sample_size)
            
            for col in candidate_cols:
                distinct_ratio = df_sample[col].nunique() / sample_size
                if distinct_ratio > distinct_value_threshold:
                    high_card_cols.append(col)
                else:
                    low_card_cols.append(col)
        else:
            low_card_cols = candidate_cols

        # Step 3: Find optimal order for low-cardinality columns via greedy search
        best_order_low = []
        remaining_cols = low_card_cols.copy()
        
        for _ in range(len(low_card_cols)):
            if not remaining_cols:
                break

            if len(remaining_cols) == 1:
                best_col = remaining_cols[0]
            elif parallel and len(remaining_cols) > 1:
                candidate_col_lists = [best_order_low + [col] for col in remaining_cols]
                scores = Parallel(n_jobs=-1, prefer="threads")(
                    delayed(_calculate_distinct_count)(cols, df_str) for cols in candidate_col_lists
                )
                min_idx = np.argmin(scores)
                best_col = remaining_cols[min_idx]
            else:
                min_distinct_count = float('inf')
                best_col_candidate = None
                for col in remaining_cols:
                    current_cols = best_order_low + [col]
                    distinct_count = _calculate_distinct_count(current_cols, df_str)
                    if distinct_count < min_distinct_count:
                        min_distinct_count = distinct_count
                        best_col_candidate = col
                best_col = best_col_candidate

            if best_col is not None:
                best_order_low.append(best_col)
                remaining_cols.remove(best_col)
        
        # Step 4: Order high-cardinality columns by their own cardinality
        best_order_high = []
        if high_card_cols:
            if n_rows > 0:
                cardinalities = df_str[high_card_cols].nunique()
                best_order_high = cardinalities.sort_values().index.tolist()
            else:
                best_order_high = sorted(high_card_cols)
            
        # Step 5: Combine orders and return the reordered DataFrame
        final_order = best_order_low + best_order_high
        
        if len(final_order) != num_cols or len(set(final_order)) != num_cols:
            return work_df # Fallback to original order

        return work_df[final_order]
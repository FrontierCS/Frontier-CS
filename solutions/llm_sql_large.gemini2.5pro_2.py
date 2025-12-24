import pandas as pd
import numpy as np
from multiprocessing import Pool, cpu_count
from functools import partial

# This function must be defined at the top level for multiprocessing to work.
def _score_column_worker(col, col_to_idx, df_values, active_partitions):
    """
    Calculates the score for a single column.
    The score is the number of new partitions this column would create in the active partitions.
    """
    col_idx = col_to_idx[col]
    score = 0
    for p_indices_set in active_partitions:
        # Slicing numpy array is faster with a list/array of indices
        p_indices = list(p_indices_set)
        partition_values = df_values[p_indices, col_idx]
        score += len(np.unique(partition_values))
    return col, score

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
        
        # Handle column merges
        if col_merge:
            df = df.copy()
            new_cols_data = {}
            cols_to_drop = set()
            
            for merge_group in col_merge:
                if len(merge_group) > 1 and all(c in df.columns for c in merge_group):
                    new_col_name = "_".join(map(str, merge_group))
                    new_cols_data[new_col_name] = df[merge_group].astype(str).apply("".join, axis=1)
                    for col in merge_group:
                        cols_to_drop.add(col)

            if cols_to_drop:
                df = df.drop(columns=list(cols_to_drop))
            for new_col_name, new_col_series in new_cols_data.items():
                df[new_col_name] = new_col_series

        columns_to_order = list(df.columns)
        if not columns_to_order:
            return df
            
        num_rows = df.shape[0]
        if num_rows == 0:
            return df

        final_order = []

        # Greedy phase to find the best initial columns
        if col_stop > 0:
            partitions = {frozenset(range(num_rows))}
            
            df_values = df.to_numpy()
            col_to_idx = {col: i for i, col in enumerate(df.columns)}

            for _ in range(min(col_stop, len(df.columns))):
                if not columns_to_order:
                    break

                active_partitions = {p for p in partitions if len(p) > row_stop}
                if not active_partitions:
                    break

                best_col = None
                
                # Score candidate columns
                if parallel and len(columns_to_order) > 1:
                    worker_func = partial(
                        _score_column_worker,
                        col_to_idx=col_to_idx,
                        df_values=df_values,
                        active_partitions=active_partitions,
                    )
                    num_processes = min(cpu_count(), len(columns_to_order))
                    with Pool(processes=num_processes) as pool:
                        scores = pool.map(worker_func, columns_to_order)
                    
                    scores_dict = dict(scores)
                    if scores_dict:
                        best_col = min(scores_dict, key=scores_dict.get)
                else: 
                    min_score = float('inf')
                    for col in columns_to_order:
                        _, score = _score_column_worker(col, col_to_idx, df_values, active_partitions)
                        if score < min_score:
                            min_score = score
                            best_col = col

                if best_col is None:
                    break

                final_order.append(best_col)
                columns_to_order.remove(best_col)

                # Update partitions based on the chosen column
                new_partitions = set()
                for part in partitions:
                    if len(part) <= row_stop:
                        new_partitions.add(part)
                        continue
                    
                    part_list = list(part)
                    p_df = df.iloc[part_list]
                    sub_groups = p_df.groupby(best_col, sort=False)
                    
                    if sub_groups.ngroups <= 1:
                        new_partitions.add(part)
                    else:
                        for _, group_indices in sub_groups.groups.items():
                            new_partitions.add(frozenset(group_indices.tolist()))
                
                partitions = new_partitions

                if len(partitions) > early_stop:
                    break
        
        # Heuristic phase for remaining columns
        if columns_to_order:
            remaining_cols_nunique = df[columns_to_order].nunique()
            
            low_card_rem = [
                c for c in columns_to_order 
                if (remaining_cols_nunique[c] / num_rows) < distinct_value_threshold
            ]
            high_card_rem = [
                c for c in columns_to_order if c not in low_card_rem
            ]

            low_card_rem.sort(key=lambda c: remaining_cols_nunique[c])
            high_card_rem.sort(key=lambda c: remaining_cols_nunique[c])
            
            final_order.extend(low_card_rem)
            final_order.extend(high_card_rem)
        
        # Ensure all columns are included in the final order
        if len(final_order) != len(df.columns):
            current_cols = set(final_order)
            missing_cols = [c for c in df.columns if c not in current_cols]
            if missing_cols:
                missing_cols_nunique = df[missing_cols].nunique()
                missing_cols.sort(key=lambda c: missing_cols_nunique[c])
                final_order.extend(missing_cols)
        
        return df[final_order]

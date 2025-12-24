import pandas as pd
import numpy as np
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict
import itertools

# This helper function is defined at the module level for compatibility with some
# parallel processing backends that have trouble with nested function pickling.
def _calculate_gain_static(prefixes_and_values):
    """
    Helper function for parallel execution.
    Calculates the LCP score gain for a new column.
    """
    prefixes, col_values = prefixes_and_values
    score_gain = 0
    # Using defaultdict for efficient grouping
    groups = defaultdict(list)
    for p, v in zip(prefixes, col_values):
        groups[p].append(v)
    
    for group_vals in groups.values():
        if len(group_vals) > 1:
            # Using numpy for fast sorting of string arrays
            sorted_vals = np.sort(group_vals)
            for i in range(len(sorted_vals) - 1):
                # os.path.commonprefix is implemented in C and is very fast
                score_gain += len(os.path.commonprefix([sorted_vals[i], sorted_vals[i+1]]))
    return score_gain


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
        df_processed = df.copy()

        if col_merge:
            # Flatten the list of columns to be merged and remove duplicates
            cols_to_drop = set(itertools.chain.from_iterable(col_merge))
            
            for i, group in enumerate(col_merge):
                if not group or not all(c in df_processed.columns for c in group):
                    continue
                new_col_name = f"__merged_{i}__"
                df_processed[new_col_name] = df_processed[group].astype(str).apply("".join, axis=1)
            
            # Drop the original columns that have been merged
            df_processed = df_processed.drop(columns=[c for c in cols_to_drop if c in df_processed.columns])

        df_str = df_processed.astype(str)
        all_cols = list(df_str.columns)
        num_cols = len(all_cols)

        if num_cols <= 1:
            return df_processed

        beam_width = row_stop
        
        # --- Beam Search for the first `col_stop` columns ---
        beams = [([], 0.0)]  # List of (order, score)

        for k in range(min(col_stop, num_cols)):
            if not beams or not beams[0][0]: # Handle first iteration or empty beams
                if not any(c for c, _ in beams): # all orders are empty
                    prefixes_for_all = pd.Series([""] * len(df_str), index=df_str.index)

            candidates = []
            tasks = []
            
            prefixes_cache = {}
            for current_order, current_score in beams:
                order_tuple = tuple(current_order)
                if order_tuple not in prefixes_cache:
                    if not current_order:
                        prefixes = prefixes_for_all
                    else:
                        prefixes = df_str[current_order].apply("".join, axis=1)
                    prefixes_cache[order_tuple] = prefixes
                
                prefixes = prefixes_cache[order_tuple]
                
                remaining_cols = [c for c in all_cols if c not in current_order]
                for col in remaining_cols:
                    tasks.append({
                        "order": current_order,
                        "score": current_score,
                        "col": col,
                        "prefixes": prefixes
                    })

            if parallel and len(tasks) > 1:
                with ProcessPoolExecutor() as executor:
                    future_to_task = {
                        executor.submit(_calculate_gain_static, (task["prefixes"].to_numpy(dtype=str), df_str[task["col"]].to_numpy(dtype=str))): task
                        for task in tasks
                    }
                    for future in as_completed(future_to_task):
                        task = future_to_task[future]
                        score_gain = future.result()
                        candidates.append((task["order"] + [task["col"]], task["score"] + score_gain))
            else:
                for task in tasks:
                    score_gain = _calculate_gain_static((task["prefixes"].to_numpy(dtype=str), df_str[task["col"]].to_numpy(dtype=str)))
                    candidates.append((task["order"] + [task["col"]], task["score"] + score_gain))

            if not candidates:
                break

            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Prune to beam width, ensuring unique orders
            new_beams = []
            seen_orders = set()
            for order, score in candidates:
                order_tuple = tuple(order)
                if order_tuple not in seen_orders:
                    new_beams.append((order, score))
                    seen_orders.add(order_tuple)
                    if len(new_beams) == beam_width:
                        break
            beams = new_beams if new_beams else [([], 0.0)]

        best_order_prefix = beams[0][0]
        
        # --- Heuristic for remaining columns ---
        remaining_cols = [c for c in all_cols if c not in best_order_prefix]
        
        if remaining_cols:
            n_rows = len(df_str)
            if n_rows > 0:
                nuniques = {c: df_str[c].nunique() for c in remaining_cols}
                
                low_card = [c for c in remaining_cols if nuniques[c] / n_rows <= distinct_value_threshold]
                high_card = [c for c in remaining_cols if nuniques[c] / n_rows > distinct_value_threshold]
                
                low_card.sort(key=lambda c: nuniques[c])
                high_card.sort(key=lambda c: nuniques[c])
                
                best_order_prefix.extend(low_card)
                best_order_prefix.extend(high_card)

        final_order = best_order_prefix if best_order_prefix else all_cols
        
        return df_processed[final_order]

import pandas as pd
import numpy as np
from joblib import Parallel, delayed
from typing import List, Tuple

def _calculate_score_static(col: str, df_sample_str: pd.DataFrame, group_ids: pd.Series) -> Tuple[str, float]:
    """
    Calculates the grouping score for a candidate column. This function is defined at the
    top level to ensure compatibility with multiprocessing-based parallel backends.

    The score is the sum of squares of subgroup sizes formed by adding the new column.
    Maximizing this score is equivalent to minimizing the entropy of the new partitioning,
    effectively favoring columns that preserve existing large groups.

    Args:
        col: The name of the candidate column to score.
        df_sample_str: DataFrame of string-converted sample data.
        group_ids: A Series mapping each sample row to its current group ID.

    Returns:
        A tuple containing the column name and its calculated score.
    """
    try:
        subgroup_sizes = df_sample_str.groupby(
            [group_ids, df_sample_str[col]], observed=True, sort=False
        ).size()
        score = np.sum(subgroup_sizes.values ** 2)
        return col, float(score)
    except Exception:
        return col, 0.0

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
        Reorders columns in the DataFrame to maximize prefix hit rate.

        The strategy is a hybrid greedy approach:
        1.  A limited-step greedy search identifies the optimal initial set of columns,
            considering inter-column dependencies. This is the most critical part for
            establishing long common prefixes.
        2.  The remaining columns are sorted by a simpler, faster heuristic (cardinality),
            as their impact on the overall hit rate is progressively smaller.
        3.  High-cardinality columns, which are detrimental to prefix matching, are
            identified and moved to the end.
        4.  The entire process is performed on a data sample to meet the strict runtime
            constraints, and parallel processing is used to accelerate the greedy search.
        """
        # 1. Handle Column Merges
        df_processed = df.copy()
        if col_merge:
            all_merged_cols = set()
            new_cols_data = {}
            for i, group in enumerate(col_merge):
                if not isinstance(group, list) or not group:
                    continue
                
                valid_group = [c for c in group if c in df_processed.columns]
                if not valid_group:
                    continue
                
                new_col_name = f"__merged_{i}"
                new_cols_data[new_col_name] = df_processed[valid_group].astype(str).agg("".join, axis=1)
                all_merged_cols.update(valid_group)
            
            if all_merged_cols:
                df_processed.drop(columns=list(all_merged_cols), inplace=True)
                for name, data in new_cols_data.items():
                    df_processed[name] = data
        
        if df_processed.shape[1] <= 1:
            return df_processed

        # 2. Prepare for Search using a Sample
        sample_size = min(len(df_processed), 4000)
        df_sample = df_processed.sample(n=sample_size, random_state=42)
        
        nunique = df_sample.nunique()
        
        # 3. Partition columns into low and high cardinality groups
        high_card_cols = {
            c for c, n in nunique.items() 
            if (n / sample_size) > distinct_value_threshold and n > 10
        }
        candidates = [c for c in df_processed.columns if c not in high_card_cols]
        
        df_sample_str = df_sample[candidates].astype(str)

        # 4. Greedy search for the best prefix
        ordered_prefix = []
        group_ids = pd.Series(0, index=df_sample.index, dtype=np.int32)
        
        num_greedy_steps = min(len(candidates), col_stop)

        for _ in range(num_greedy_steps):
            if not candidates:
                break
            
            scores = {}
            if parallel and len(candidates) > 1:
                with Parallel(n_jobs=-1, prefer="threads") as parallel_runner:
                    results = parallel_runner(
                        delayed(_calculate_score_static)(c, df_sample_str, group_ids)
                        for c in candidates
                    )
                scores = dict(results)
            else:
                for col in candidates:
                    _, score = _calculate_score_static(col, df_sample_str, group_ids)
                    scores[col] = score

            if not scores:
                break

            best_col = max(scores, key=scores.get)
            
            ordered_prefix.append(best_col)
            candidates.remove(best_col)
            
            if not candidates:
                break
                
            # Update group_ids efficiently by factorizing tuples of (old_id, new_value)
            group_ids = pd.Series(
                pd.factorize(list(zip(group_ids, df_sample_str[best_col])))[0],
                index=df_sample.index,
                dtype=np.int32
            )
            
        # 5. Order remaining columns based on cardinality
        remaining_candidates_sorted = sorted(candidates, key=lambda c: nunique[c])
        high_card_cols_sorted = sorted(list(high_card_cols), key=lambda c: nunique[c])
        
        # 6. Combine ordered column sets to get the final order
        final_order = ordered_prefix + remaining_candidates_sorted + high_card_cols_sorted
        
        # Fallback mechanism in case of column mismatch
        if len(final_order) != df_processed.shape[1] or len(set(final_order)) != df_processed.shape[1]:
            all_cols_sorted = sorted(
                df_processed.columns.tolist(),
                key=lambda c: nunique.get(c, df_processed.shape[0])
            )
            return df_processed[all_cols_sorted]

        return df_processed[final_order]
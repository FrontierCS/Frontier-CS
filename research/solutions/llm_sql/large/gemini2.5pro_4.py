import pandas as pd
import numpy as np
from joblib import Parallel, delayed
from typing import List, Dict, Tuple

# This helper function is defined at the top level for better compatibility
# with multiprocessing libraries like joblib.
def _expand_beam_state(
    p: List[str],
    groups: pd.Series,
    search_cols: List[str],
    stats: Dict[str, int],
    df_sample: pd.DataFrame,
    col_stop: int,
) -> List[Tuple[List[str], float, pd.Series]]:
    """
    Expands a single state in the beam search. A state consists of the current
    partial permutation `p` and the corresponding row groupings `groups`.
    It explores `col_stop` best next columns and returns new states.
    """
    remaining = [c for c in search_cols if c not in p]
    
    # Heuristically select best candidate columns based on pre-calculated stats
    # (number of unique values). Columns with fewer unique values are preferred
    # as they create larger groups.
    candidates = sorted(remaining, key=lambda c: stats[c])[:col_stop]
    
    new_states = []
    for c in candidates:
        p_new = p + [c]
        
        # Efficiently compute new groups and the associated score.
        # New groups are formed by the combination of old groups and new column values.
        # String concatenation is a fast way to create unique keys for this combination.
        # df_sample columns are already strings, and groups is int, but astype(str) is safe.
        combined_keys = groups.astype(str) + '_' + df_sample[c]
        
        # `pd.factorize` is a fast way to convert keys to integer-based group IDs.
        new_group_codes = pd.factorize(combined_keys)[0]
        
        # The score is the sum of squares of group sizes. This rewards creating
        # large, homogeneous groups, which directly correlates with longer LCPs.
        _, counts = np.unique(new_group_codes, return_counts=True)
        score = np.sum(np.square(counts, dtype=np.uint64)) # Use uint64 for large counts
        
        new_groups = pd.Series(new_group_codes, index=df_sample.index, dtype='int32')
        new_states.append((p_new, score, new_groups))
        
    return new_states


class Solution:
    """
    Implements a solution to reorder CSV columns to maximize KV-cache hit rate.
    The core of the solution is a beam search algorithm to find a near-optimal
    column order that maximizes prefix similarity across rows.
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
        1. Pre-process columns by merging specified groups.
        2. Analyze columns on a sample of the data to classify them.
        3. Partition columns into three groups:
           - Constant columns (1 unique value): Placed first.
           - High-cardinality columns (likely IDs): Placed last.
           - Low-cardinality columns: The main target for optimization.
        4. Use a beam search algorithm to find the best ordering for low-cardinality columns.
           The search aims to find a permutation that maximizes group cohesion at each step.
        5. Combine the ordered partitions to get the final column order.
        """
        if df.empty:
            return df

        df_processed = self._handle_merges(df, col_merge)
        original_cols = df_processed.columns.tolist()

        if len(original_cols) <= 1:
            return df_processed
            
        n_rows = df_processed.shape[0]
        sample_size = min(n_rows, early_stop)
        # Convert sample to string once to avoid repeated conversions.
        df_sample = df_processed.head(sample_size).astype(str, copy=False)

        stats = {c: df_sample[c].nunique() for c in df_sample.columns}

        const_cols = [c for c, n in stats.items() if n == 1]
        
        high_card_cols = [
            c for c, n in stats.items()
            if (n > 1 and n / sample_size > distinct_value_threshold)
        ]
        
        low_card_cols = [
            c for c in original_cols if c not in const_cols and c not in high_card_cols
        ]

        # High-cardinality columns are sorted by nunique to place more unique ones later.
        p_high = sorted(high_card_cols, key=lambda c: stats[c])

        p_low = self._beam_search(
            df_sample, low_card_cols, stats, row_stop, col_stop, parallel
        )

        final_order = const_cols + p_low + p_high
        
        # Safety check to ensure all columns are included in the final order.
        if len(final_order) != len(original_cols):
             all_cols_set = set(original_cols)
             final_order_set = set(final_order)
             missing_cols = list(all_cols_set - final_order_set)
             final_order.extend(sorted(missing_cols))

        return df_processed[final_order]

    def _handle_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        if not col_merge:
            return df

        df_copy = df.copy()
        for group in col_merge:
            if not isinstance(group, list) or len(group) < 2:
                continue

            new_col_name = "_".join(map(str, group))
            # Efficiently concatenate string columns
            df_copy[new_col_name] = df_copy[group].astype(str).agg("".join, axis=1)
            df_copy = df_copy.drop(columns=group)
            
        return df_copy

    def _beam_search(
        self,
        df_sample: pd.DataFrame,
        search_cols: List[str],
        stats: Dict[str, int],
        row_stop: int, # Beam width
        col_stop: int, # Branch factor
        parallel: bool,
    ) -> List[str]:
        if not search_cols:
            return []

        # Initialize the beam with a single state: empty permutation.
        p_init = []
        groups_init = pd.Series(0, index=df_sample.index, dtype='int32')
        score_init = float(len(df_sample) ** 2)
        
        beam = [(p_init, score_init, groups_init)]

        for _ in range(len(search_cols)):
            if parallel:
                # Expand all states in the current beam in parallel.
                tasks = [
                    delayed(_expand_beam_state)(p, groups, search_cols, stats, df_sample, col_stop)
                    for p, _, groups in beam
                ]
                # Use threads as the tasks are CPU-bound with string/numpy operations that release GIL.
                results = Parallel(n_jobs=-1, prefer="threads")(tasks)
                all_candidates = [item for sublist in results for item in sublist]
            else:
                # Expand sequentially if parallel is disabled.
                all_candidates = []
                for p, _, groups in beam:
                    new_states = _expand_beam_state(p, groups, search_cols, stats, df_sample, col_stop)
                    all_candidates.extend(new_states)
            
            if not all_candidates:
                break

            # Prune candidates: sort by score, keep unique permutations, and select the top `row_stop`.
            all_candidates.sort(key=lambda x: x[1], reverse=True)
            
            unique_candidates = {}
            for p, s, g in all_candidates:
                p_tuple = tuple(p)
                if p_tuple not in unique_candidates:
                    unique_candidates[p_tuple] = (s, g)
            
            sorted_unique = sorted(unique_candidates.items(), key=lambda item: item[1][0], reverse=True)
            
            beam = [
                (list(p), s, g)
                for p, (s, g) in sorted_unique[:row_stop]
            ]
        
        if not beam:
            # Fallback if search fails, though this is unlikely.
            return sorted(search_cols, key=lambda c: stats[c])

        best_p, _, _ = beam[0]
        return best_p
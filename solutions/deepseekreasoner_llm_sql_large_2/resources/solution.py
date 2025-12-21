import pandas as pd
import numpy as np
import random
import math
import time
from typing import List, Tuple, Dict, Any
import multiprocessing as mp
from functools import partial

class TrieNode:
    __slots__ = ('children',)
    def __init__(self):
        self.children = {}

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
        # 1. Apply column merges if specified
        if col_merge is not None and len(col_merge) > 0:
            df = self._apply_column_merges(df, col_merge)
        
        # 2. Convert all values to strings (as they appear in CSV)
        df = df.astype(str)
        
        # 3. Extract data and column names
        original_columns = df.columns.tolist()
        M = len(original_columns)
        rows = [list(row) for row in df.itertuples(index=False, name=None)]
        N = len(rows)
        
        # 4. Determine sample size for evaluation
        sample_size = min(N, max(1000, row_stop * 500))
        if sample_size < N:
            # use first sample_size rows (preserving order)
            sample_rows = rows[:sample_size]
        else:
            sample_rows = rows
        
        # 5. Compute column statistics for initial ordering
        col_stats = []
        for col_idx in range(M):
            col_vals = [row[col_idx] for row in sample_rows]
            distinct_count = len(set(col_vals))
            distinct_ratio = distinct_count / len(sample_rows)
            avg_len = sum(len(v) for v in col_vals) / len(sample_rows)
            col_stats.append((distinct_ratio, -avg_len, col_idx))
        
        # Sort by distinct_ratio ascending, then avg_len descending
        col_stats.sort(key=lambda x: (x[0], x[1]))
        initial_order = [idx for _, _, idx in col_stats]
        
        # 6. Precompute column strings for sampled rows to avoid repeated conversion
        # rows are already strings, so just keep as list of lists
        
        # 7. Define evaluation function using trie
        def evaluate_order(order: List[int], rows_data: List[List[str]]) -> float:
            """Return total matched prefix length for the given column order."""
            root = TrieNode()
            total_matched = 0
            for row in rows_data:
                node = root
                matched = True
                depth = 0
                for col_idx in order:
                    s = row[col_idx]
                    for ch in s:
                        if matched and ch in node.children:
                            depth += 1
                            node = node.children[ch]
                        else:
                            if matched:
                                matched = False
                            if ch not in node.children:
                                node.children[ch] = TrieNode()
                            node = node.children[ch]
                total_matched += depth
            return total_matched
        
        # 8. Local search with simulated annealing
        best_order = initial_order[:]
        best_score = evaluate_order(best_order, sample_rows)
        current_order = initial_order[:]
        current_score = best_score
        
        T_start = 1.0
        T_end = 0.001
        cooling = 0.995
        T = T_start
        no_improve = 0
        max_iter = 5000  # safety limit, will break on time or early_stop
        start_time = time.time()
        time_limit = 8.0  # leave 2 seconds for final DataFrame reordering
        
        for it in range(max_iter):
            # Time check
            if time.time() - start_time > time_limit:
                break
            if no_improve >= early_stop:
                break
            
            # Generate new order by swapping two random columns
            i, j = random.sample(range(M), 2)
            new_order = current_order[:]
            new_order[i], new_order[j] = new_order[j], new_order[i]
            new_score = evaluate_order(new_order, sample_rows)
            
            # Update best
            if new_score > best_score:
                best_score = new_score
                best_order = new_order[:]
                no_improve = 0
            else:
                no_improve += 1
            
            # Simulated annealing acceptance
            if new_score > current_score:
                current_order, current_score = new_order, new_score
            else:
                delta = new_score - current_score
                if random.random() < math.exp(delta / T):
                    current_order, current_score = new_order, new_score
            
            T *= cooling
            if T < T_end:
                T = T_end
        
        # 9. Apply the best order to the full DataFrame
        reordered_cols = [original_columns[i] for i in best_order]
        result_df = df[reordered_cols]
        return result_df
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: List[List[str]]) -> pd.DataFrame:
        """Merge columns as specified. Each group becomes a single column with concatenated values."""
        df = df.copy()
        new_columns = {}
        cols_to_drop = []
        for idx, group in enumerate(col_merge):
            if not all(col in df.columns for col in group):
                continue
            merged_name = f"__merged_{idx}"
            # Concatenate without spaces
            new_columns[merged_name] = df[group].apply(lambda row: ''.join(row.astype(str)), axis=1)
            cols_to_drop.extend(group)
        # Add new merged columns
        for name, col in new_columns.items():
            df[name] = col
        # Drop original columns that were merged
        df = df.drop(columns=cols_to_drop)
        return df

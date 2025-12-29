import pandas as pd
import numpy as np
from collections import defaultdict
from itertools import permutations
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

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
        # Apply column merges if specified
        if col_merge:
            df = self._apply_column_merges(df, col_merge)
        
        # Convert all values to strings
        df = df.astype(str)
        
        # Get column names
        columns = list(df.columns)
        n_cols = len(columns)
        
        # If only one column, return as is
        if n_cols <= 1:
            return df
        
        # Preprocess: compute column statistics
        col_stats = self._compute_column_stats(df, columns, distinct_value_threshold)
        
        # Generate initial candidate order using heuristic
        initial_order = self._generate_initial_order(columns, col_stats, n_cols)
        
        # Evaluate initial order
        best_order = initial_order
        best_score = self._evaluate_order(df, initial_order)
        
        # If few columns, try all permutations (n_cols ≤ 5)
        if n_cols <= 5:
            all_orders = list(permutations(columns))
            for order in all_orders[:min(early_stop, len(all_orders))]:
                score = self._evaluate_order(df, order)
                if score > best_score:
                    best_score = score
                    best_order = order
        
        # For more columns, use beam search with heuristic
        else:
            # Generate candidate orders using beam search
            candidates = self._beam_search(
                df, columns, col_stats, 
                early_stop, row_stop, col_stop,
                best_order, best_score, parallel
            )
            
            # Evaluate candidates
            for order, score in candidates:
                if score > best_score:
                    best_score = score
                    best_order = order
        
        return df[list(best_order)]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Apply column merges as specified."""
        df = df.copy()
        for merge_group in col_merge:
            if not merge_group:
                continue
            
            # Create merged column by concatenating values
            merged_name = "_".join(merge_group)
            df[merged_name] = df[merge_group].apply(
                lambda row: "".join(str(x) for x in row), axis=1
            )
            
            # Remove original columns
            df = df.drop(columns=merge_group)
        
        return df
    
    def _compute_column_stats(self, df: pd.DataFrame, columns: list, threshold: float):
        """Compute statistics for each column."""
        stats = {}
        n_rows = len(df)
        
        for col in columns:
            values = df[col].values
            unique_vals = set(values)
            unique_ratio = len(unique_vals) / n_rows
            
            # Compute prefix characteristics
            sample_size = min(1000, n_rows)
            sample_indices = np.random.choice(n_rows, sample_size, replace=False)
            sample_values = [values[i] for i in sample_indices]
            
            # Estimate common prefix length within column
            avg_prefix_len = 0
            if len(sample_values) > 1:
                for i in range(len(sample_values)):
                    for j in range(i + 1, len(sample_values)):
                        s1, s2 = sample_values[i], sample_values[j]
                        lcp = self._lcp(s1, s2)
                        avg_prefix_len += lcp
                avg_prefix_len /= (len(sample_values) * (len(sample_values) - 1) / 2)
            
            # Compute value length statistics
            lengths = [len(str(v)) for v in values[:1000]]
            avg_len = np.mean(lengths) if lengths else 0
            
            stats[col] = {
                'unique_ratio': unique_ratio,
                'avg_prefix_len': avg_prefix_len,
                'avg_len': avg_len,
                'is_high_entropy': unique_ratio > threshold
            }
        
        return stats
    
    def _generate_initial_order(self, columns: list, col_stats: dict, n_cols: int):
        """Generate initial column order using heuristic rules."""
        # Sort by multiple criteria:
        # 1. Low unique ratio first (more repetitive values)
        # 2. High average prefix length within column
        # 3. Shorter average length (faster to compare)
        sorted_cols = sorted(columns, key=lambda col: (
            col_stats[col]['is_high_entropy'],  # False (0) before True (1)
            col_stats[col]['unique_ratio'],
            -col_stats[col]['avg_prefix_len'],
            col_stats[col]['avg_len']
        ))
        
        return tuple(sorted_cols)
    
    def _beam_search(self, df, columns, col_stats, early_stop, row_stop, col_stop, 
                    initial_order, initial_score, parallel):
        """Perform beam search for column ordering."""
        n_cols = len(columns)
        beam_width = min(100, early_stop // 10)
        
        # Start with initial candidate
        candidates = [(initial_order, initial_score)]
        
        # Limit search space based on early_stop
        max_iterations = min(100, early_stop // (beam_width * n_cols))
        
        for _ in range(max_iterations):
            new_candidates = []
            
            # Generate neighbors by swapping columns
            for order, score in candidates:
                # Generate neighbors by swapping pairs
                for i in range(min(n_cols, col_stop)):
                    for j in range(i + 1, n_cols):
                        new_order = list(order)
                        new_order[i], new_order[j] = new_order[j], new_order[i]
                        new_order = tuple(new_order)
                        
                        # Evaluate on subset of rows for speed
                        if row_stop > 0:
                            subset_score = self._evaluate_order_subset(df, new_order, row_stop)
                        else:
                            subset_score = self._evaluate_order(df, new_order)
                        
                        new_candidates.append((new_order, subset_score))
            
            # Keep top candidates
            new_candidates.sort(key=lambda x: x[1], reverse=True)
            candidates = new_candidates[:beam_width]
            
            # Early stopping if no improvement
            if len(candidates) > 0 and candidates[0][1] <= initial_score:
                break
        
        return candidates
    
    def _evaluate_order(self, df: pd.DataFrame, order: tuple) -> float:
        """Evaluate a column order by computing actual hit rate."""
        n_rows = len(df)
        if n_rows <= 1:
            return 0.0
        
        # Build concatenated strings
        strings = []
        total_len = 0
        
        for idx, row in df[list(order)].iterrows():
            s = "".join(str(x) for x in row)
            strings.append(s)
            total_len += len(s)
        
        # Compute LCP sum using optimized method
        lcp_sum = 0
        
        # Use a trie-like structure for efficient LCP computation
        root = {}
        
        for i, s in enumerate(strings):
            if i == 0:
                # Insert first string
                node = root
                for ch in s:
                    if ch not in node:
                        node[ch] = {}
                    node = node[ch]
                continue
            
            # Find LCP with previous strings using the trie
            node = root
            lcp = 0
            for ch in s:
                if ch in node:
                    node = node[ch]
                    lcp += 1
                else:
                    break
            
            lcp_sum += lcp
            
            # Insert current string into trie
            node = root
            for ch in s:
                if ch not in node:
                    node[ch] = {}
                node = node[ch]
        
        return lcp_sum / total_len if total_len > 0 else 0.0
    
    def _evaluate_order_subset(self, df: pd.DataFrame, order: tuple, subset_size: int) -> float:
        """Evaluate order on a subset of rows for faster computation."""
        n_rows = len(df)
        if n_rows <= 1:
            return 0.0
        
        # Use random subset
        if subset_size < n_rows:
            indices = np.random.choice(n_rows, min(subset_size, n_rows), replace=False)
            df_subset = df.iloc[indices].copy()
        else:
            df_subset = df
        
        return self._evaluate_order(df_subset, order)
    
    def _lcp(self, s1: str, s2: str) -> int:
        """Compute longest common prefix between two strings."""
        i = 0
        min_len = min(len(s1), len(s2))
        while i < min_len and s1[i] == s2[i]:
            i += 1
        return i
import pandas as pd
import numpy as np
from itertools import permutations, combinations
from collections import defaultdict, Counter
import time
from typing import List, Tuple, Dict, Set
import multiprocessing as mp
from functools import partial
import heapq

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
        start_time = time.time()
        
        # Apply column merges if specified
        if col_merge:
            df = self._apply_column_merges(df, col_merge)
        
        # If only 1 column, return as is
        if len(df.columns) <= 1:
            return df
        
        # Convert all values to strings and cache
        df_str = df.astype(str)
        
        # Analyze column properties
        col_stats = self._analyze_columns(df_str)
        
        # Get column order using optimization algorithm
        col_order = self._optimize_column_order(
            df_str, col_stats, early_stop, distinct_value_threshold, parallel
        )
        
        # Return DataFrame with optimized column order
        return df[col_order]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Apply column merge operations."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if len(merge_group) < 2:
                continue
                
            # Merge columns by concatenating their string values
            merged_col = merge_group[0]
            result_df[merged_col] = result_df[merge_group].astype(str).agg(''.join, axis=1)
            
            # Drop the other columns in the merge group
            cols_to_drop = [col for col in merge_group[1:] if col in result_df.columns]
            result_df = result_df.drop(columns=cols_to_drop)
        
        return result_df
    
    def _analyze_columns(self, df_str: pd.DataFrame) -> Dict:
        """Analyze column statistics for optimization."""
        n_rows = len(df_str)
        n_cols = len(df_str.columns)
        
        stats = {
            'n_unique': {},
            'entropy': {},
            'prefix_potential': {},
            'column_lengths': {}
        }
        
        for col in df_str.columns:
            values = df_str[col].values
            stats['n_unique'][col] = len(set(values))
            stats['column_lengths'][col] = sum(len(str(v)) for v in values) / n_rows
            
            # Calculate entropy (simplified)
            value_counts = Counter(values)
            entropy = 0
            for count in value_counts.values():
                p = count / n_rows
                entropy -= p * np.log2(p + 1e-10)
            stats['entropy'][col] = entropy
            
            # Estimate prefix potential
            prefix_potential = 0
            for i in range(min(1000, n_rows)):
                for j in range(i + 1, min(i + 10, n_rows)):
                    if values[i] == values[j]:
                        prefix_potential += 1
            stats['prefix_potential'][col] = prefix_potential
        
        return stats
    
    def _optimize_column_order(
        self, 
        df_str: pd.DataFrame,
        col_stats: Dict,
        early_stop: int,
        distinct_value_threshold: float,
        parallel: bool
    ) -> List:
        """Optimize column order for maximum prefix hit rate."""
        n_cols = len(df_str.columns)
        columns = list(df_str.columns)
        
        # For small number of columns, try all permutations (max 10! = 3.6M, too large)
        # We'll use heuristic search with beam search
        
        if n_cols <= 5:
            # Try all permutations for small number of columns
            return self._exhaustive_search(df_str, columns)
        else:
            # Use beam search with heuristic initialization
            return self._beam_search(df_str, columns, col_stats, beam_width=100)
    
    def _exhaustive_search(self, df_str: pd.DataFrame, columns: List) -> List:
        """Exhaustive search for small number of columns."""
        best_order = columns
        best_score = self._evaluate_order(df_str, columns)
        
        # Try all permutations (only for n <= 5)
        for perm in permutations(columns):
            score = self._evaluate_order(df_str, perm)
            if score > best_score:
                best_score = score
                best_order = list(perm)
        
        return best_order
    
    def _beam_search(
        self, 
        df_str: pd.DataFrame, 
        columns: List,
        col_stats: Dict,
        beam_width: int = 100
    ) -> List:
        """Beam search for column ordering."""
        n_cols = len(columns)
        
        # Initialize with heuristic orderings
        beam = []
        
        # Heuristic 1: Sort by number of unique values (ascending)
        order1 = sorted(columns, key=lambda x: col_stats['n_unique'][x])
        beam.append((self._evaluate_order(df_str, order1), order1))
        
        # Heuristic 2: Sort by entropy (ascending)
        order2 = sorted(columns, key=lambda x: col_stats['entropy'][x])
        beam.append((self._evaluate_order(df_str, order2), order2))
        
        # Heuristic 3: Sort by prefix potential (descending)
        order3 = sorted(columns, key=lambda x: -col_stats['prefix_potential'][x])
        beam.append((self._evaluate_order(df_str, order3), order3))
        
        # Generate random permutations for initial beam
        import random
        for _ in range(min(beam_width - 3, 50)):
            random_order = columns.copy()
            random.shuffle(random_order)
            score = self._evaluate_order(df_str, random_order)
            beam.append((score, random_order))
        
        # Keep top beam_width candidates
        beam.sort(reverse=True, key=lambda x: x[0])
        beam = beam[:beam_width]
        
        # Beam search iterations
        for _ in range(min(3, n_cols)):  # Limited iterations for time
            new_beam = []
            
            for score, order in beam:
                # Generate neighbors by swapping adjacent columns
                for i in range(n_cols - 1):
                    new_order = order.copy()
                    new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                    new_score = self._evaluate_order(df_str, new_order)
                    new_beam.append((new_score, new_order))
            
            # Also try inserting each column at different positions
            for score, order in beam:
                for i in range(n_cols):
                    for j in range(n_cols):
                        if i != j:
                            new_order = order.copy()
                            col = new_order.pop(i)
                            new_order.insert(j, col)
                            new_score = self._evaluate_order(df_str, new_order)
                            new_beam.append((new_score, new_order))
            
            # Combine and keep best
            beam.extend(new_beam)
            beam.sort(reverse=True, key=lambda x: x[0])
            beam = beam[:beam_width]
        
        # Return best order
        return beam[0][1]
    
    def _evaluate_order(self, df_str: pd.DataFrame, order: List) -> float:
        """
        Evaluate the prefix hit rate for a given column order.
        Uses efficient incremental computation.
        """
        n_rows = len(df_str)
        if n_rows <= 1:
            return 0.0
        
        # Concatenate columns in given order
        strings = []
        for idx in range(n_rows):
            row_str = ''.join(str(df_str.iloc[idx][col]) for col in order)
            strings.append(row_str)
        
        # Compute prefix hit rate incrementally
        total_lcp = 0
        total_length = 0
        
        # Use a trie for efficient LCP computation
        trie = {}
        
        for i in range(n_rows):
            s = strings[i]
            total_length += len(s)
            
            if i == 0:
                # First row: insert into trie
                node = trie
                for ch in s:
                    if ch not in node:
                        node[ch] = {}
                    node = node[ch]
                continue
            
            # Find LCP with previous rows using trie
            node = trie
            lcp = 0
            for ch in s:
                if ch in node:
                    lcp += 1
                    node = node[ch]
                else:
                    break
            
            total_lcp += lcp
            
            # Insert current string into trie
            node = trie
            for ch in s:
                if ch not in node:
                    node[ch] = {}
                node = node[ch]
        
        if total_length == 0:
            return 0.0
        
        return total_lcp / total_length
    
    def _greedy_optimization(self, df_str: pd.DataFrame) -> List:
        """Greedy optimization starting from best heuristic."""
        columns = list(df_str.columns)
        n_cols = len(columns)
        
        if n_cols <= 1:
            return columns
        
        # Start with columns sorted by number of unique values
        current_order = sorted(columns, key=lambda x: len(set(df_str[x])))
        current_score = self._evaluate_order(df_str, current_order)
        
        improved = True
        while improved:
            improved = False
            
            # Try all pairwise swaps
            for i in range(n_cols):
                for j in range(i + 1, n_cols):
                    new_order = current_order.copy()
                    new_order[i], new_order[j] = new_order[j], new_order[i]
                    new_score = self._evaluate_order(df_str, new_order)
                    
                    if new_score > current_score:
                        current_order = new_order
                        current_score = new_score
                        improved = True
                        break
                if improved:
                    break
        
        return current_order

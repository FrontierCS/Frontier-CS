import pandas as pd
import numpy as np
from collections import defaultdict
from itertools import permutations, combinations
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
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
        
        # Start timing
        start_time = time.time()
        
        # Apply column merges if specified
        if col_merge:
            df = self._apply_column_merges(df, col_merge)
        
        # If DataFrame is empty or has only 1 column, return as is
        if len(df.columns) <= 1:
            return df
        
        # Get column names
        columns = list(df.columns)
        m = len(columns)
        
        # Convert DataFrame to string matrix
        str_matrix = df.astype(str).values
        
        # If m is small, try all permutations
        if m <= 6:
            best_order, _ = self._exact_search(str_matrix, columns)
        else:
            # Use heuristic search for larger m
            if parallel and m > 3:
                best_order = self._parallel_heuristic_search(str_matrix, columns, 
                                                            early_stop, row_stop)
            else:
                best_order = self._heuristic_search(str_matrix, columns, 
                                                   early_stop, row_stop)
        
        # Reorder DataFrame columns
        result = df[best_order]
        
        # Check runtime constraint
        elapsed = time.time() - start_time
        if elapsed > 10.0:
            # Fallback to original order if timeout
            return df
        
        return result
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Merge columns as specified in col_merge list."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if not all(col in result_df.columns for col in merge_group):
                continue
            
            # Create merged column
            merged_name = f"merged_{'_'.join(merge_group)}"
            merged_values = []
            
            for idx in range(len(result_df)):
                row_values = [str(result_df.iloc[idx][col]) for col in merge_group]
                merged_values.append(''.join(row_values))
            
            # Add merged column
            result_df[merged_name] = merged_values
            
            # Remove original columns
            result_df = result_df.drop(columns=merge_group)
        
        return result_df
    
    def _exact_search(self, matrix: np.ndarray, columns: list):
        """Try all permutations for small number of columns."""
        m = len(columns)
        best_score = -1
        best_order = None
        
        for perm in permutations(range(m)):
            order = [columns[i] for i in perm]
            score = self._evaluate_order(matrix, perm)
            if score > best_score:
                best_score = score
                best_order = order
        
        return best_order, best_score
    
    def _heuristic_search(self, matrix: np.ndarray, columns: list,
                         early_stop: int, row_stop: int):
        """Heuristic search for column ordering."""
        m = len(columns)
        
        # Start with random order
        current_order = list(range(m))
        np.random.shuffle(current_order)
        current_score = self._evaluate_order(matrix, current_order)
        
        # Local search with swaps
        improved = True
        iteration = 0
        
        while improved and iteration < 100:
            improved = False
            iteration += 1
            
            # Try all pairwise swaps
            for i in range(m):
                for j in range(i + 1, m):
                    if iteration > 50 and np.random.random() > 0.7:
                        continue  # Early stopping for later iterations
                    
                    new_order = current_order.copy()
                    new_order[i], new_order[j] = new_order[j], new_order[i]
                    
                    new_score = self._evaluate_order(matrix, new_order)
                    
                    if new_score > current_score:
                        current_score = new_score
                        current_order = new_order
                        improved = True
                        break
                if improved:
                    break
        
        # Convert back to column names
        return [columns[i] for i in current_order]
    
    def _parallel_heuristic_search(self, matrix: np.ndarray, columns: list,
                                  early_stop: int, row_stop: int):
        """Parallel version of heuristic search."""
        m = len(columns)
        n_workers = min(mp.cpu_count(), 8)
        
        # Generate multiple starting points
        n_starts = min(20, 2 ** m)
        starts = []
        
        for _ in range(n_starts):
            order = list(range(m))
            np.random.shuffle(order)
            starts.append(order)
        
        # Evaluate in parallel
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = []
            for start_order in starts:
                future = executor.submit(self._optimize_order, matrix, start_order.copy())
                futures.append(future)
            
            best_score = -1
            best_order = None
            
            for future in as_completed(futures):
                order, score = future.result()
                if score > best_score:
                    best_score = score
                    best_order = order
        
        # Convert back to column names
        return [columns[i] for i in best_order]
    
    def _optimize_order(self, matrix: np.ndarray, start_order: list):
        """Optimize a single starting order."""
        m = len(start_order)
        current_order = start_order.copy()
        current_score = self._evaluate_order(matrix, current_order)
        
        improved = True
        iteration = 0
        
        while improved and iteration < 50:
            improved = False
            iteration += 1
            
            # Try all pairwise swaps
            for i in range(m):
                for j in range(i + 1, m):
                    if iteration > 25 and np.random.random() > 0.5:
                        continue
                    
                    new_order = current_order.copy()
                    new_order[i], new_order[j] = new_order[j], new_order[i]
                    
                    new_score = self._evaluate_order(matrix, new_order)
                    
                    if new_score > current_score:
                        current_score = new_score
                        current_order = new_order
                        improved = True
                        break
                if improved:
                    break
        
        return current_order, current_score
    
    def _evaluate_order(self, matrix: np.ndarray, order: list) -> float:
        """Evaluate the hit rate for a given column order."""
        n = len(matrix)
        if n == 0:
            return 0.0
        
        # Build strings in the given order
        strings = []
        total_length = 0
        
        for i in range(n):
            row_str = ''.join(str(matrix[i][j]) for j in order)
            strings.append(row_str)
            total_length += len(row_str)
        
        if total_length == 0:
            return 0.0
        
        # Calculate hit rate
        lcp_sum = 0
        
        # Use a trie-like structure for efficient LCP calculation
        root = {}
        
        for i in range(n):
            if i == 0:
                # Build trie for first string
                node = root
                for ch in strings[0]:
                    if ch not in node:
                        node[ch] = {}
                    node = node[ch]
                continue
            
            # Find LCP with previous strings using trie
            s = strings[i]
            node = root
            lcp = 0
            
            for ch in s:
                if ch in node:
                    lcp += 1
                    node = node[ch]
                else:
                    # Add new path to trie
                    temp_node = node
                    for ch2 in s[lcp:]:
                        temp_node[ch2] = {}
                        temp_node = temp_node[ch2]
                    break
            
            lcp_sum += lcp
        
        return lcp_sum / total_length if total_length > 0 else 0.0
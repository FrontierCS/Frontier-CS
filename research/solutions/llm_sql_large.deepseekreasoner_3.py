import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Set
import heapq
from collections import defaultdict, Counter
import itertools
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

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
        
        # If dataframe is small, use exhaustive search on subset of columns
        if len(df.columns) <= 10:
            return self._exhaustive_search(df)
        
        # Use heuristic approach for larger datasets
        return self._heuristic_reorder(df, distinct_value_threshold, parallel)
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Merge specified columns into single columns."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if not merge_group:
                continue
                
            # Create new column by concatenating values
            col_names = merge_group
            new_col_name = "_".join(col_names)
            
            # Convert to string and concatenate without spaces
            result_df[new_col_name] = result_df[col_names].astype(str).agg(''.join, axis=1)
            
            # Remove original columns
            result_df = result_df.drop(columns=col_names)
        
        return result_df
    
    def _exhaustive_search(self, df: pd.DataFrame) -> pd.DataFrame:
        """Exhaustive search for small number of columns (<=10)."""
        n_cols = len(df.columns)
        best_order = list(df.columns)
        best_score = self._compute_hit_rate(df[best_order])
        
        # Try all permutations for small n
        for perm in itertools.permutations(df.columns):
            perm = list(perm)
            score = self._compute_hit_rate(df[perm])
            if score > best_score:
                best_score = score
                best_order = perm
        
        return df[best_order]
    
    def _compute_hit_rate(self, df: pd.DataFrame) -> float:
        """Compute prefix hit rate for the given column order."""
        n_rows = len(df)
        
        # Convert each row to concatenated string
        row_strings = df.astype(str).agg(''.join, axis=1).tolist()
        
        total_lcp = 0
        total_len = 0
        
        # Use set for faster prefix matching
        prefixes = set()
        
        for i in range(n_rows):
            s = row_strings[i]
            total_len += len(s)
            
            if i == 0:
                # First row, no previous rows
                prefixes.add(s)
                continue
            
            # Find longest common prefix with any previous string
            max_lcp = 0
            # Check increasingly longer prefixes
            for prefix_len in range(len(s), 0, -1):
                prefix = s[:prefix_len]
                if prefix in prefixes:
                    max_lcp = prefix_len
                    break
            
            total_lcp += max_lcp
            prefixes.add(s)
        
        return total_lcp / total_len if total_len > 0 else 0
    
    def _heuristic_reorder(self, df: pd.DataFrame, threshold: float, parallel: bool) -> pd.DataFrame:
        """Heuristic column reordering for large datasets."""
        n_cols = len(df.columns)
        columns = list(df.columns)
        
        # Step 1: Analyze column characteristics
        col_stats = self._analyze_columns(df)
        
        # Step 2: Group columns by distinct value ratio
        high_distinct = []
        low_distinct = []
        
        for col in columns:
            distinct_ratio = col_stats[col]['distinct_ratio']
            if distinct_ratio >= threshold:
                high_distinct.append(col)
            else:
                low_distinct.append(col)
        
        # Step 3: Within each group, sort by correlation with other columns
        if parallel and len(high_distinct) > 1:
            high_order = self._parallel_greedy_order(df[high_distinct], col_stats)
        else:
            high_order = self._greedy_column_order(df[high_distinct], col_stats)
        
        if parallel and len(low_distinct) > 1:
            low_order = self._parallel_greedy_order(df[low_distinct], col_stats)
        else:
            low_order = self._greedy_column_order(df[low_distinct], col_stats)
        
        # Step 4: Combine orders - low distinct first for better prefix matching
        final_order = low_order + high_order
        
        # Step 5: Local optimization using 2-opt swaps
        optimized_order = self._local_optimization(df, final_order, col_stats)
        
        return df[optimized_order]
    
    def _analyze_columns(self, df: pd.DataFrame) -> Dict:
        """Analyze column statistics for ordering decisions."""
        col_stats = {}
        
        for col in df.columns:
            col_data = df[col]
            
            # Convert to string for analysis
            str_series = col_data.astype(str)
            
            # Distinct value ratio
            distinct_count = str_series.nunique()
            distinct_ratio = distinct_count / len(str_series)
            
            # Average string length
            avg_len = str_series.str.len().mean()
            
            # Value frequency distribution
            value_counts = str_series.value_counts()
            most_common_freq = value_counts.iloc[0] / len(str_series) if len(value_counts) > 0 else 0
            
            col_stats[col] = {
                'distinct_ratio': distinct_ratio,
                'avg_len': avg_len,
                'most_common_freq': most_common_freq,
                'total_values': len(str_series)
            }
        
        return col_stats
    
    def _greedy_column_order(self, df_subset: pd.DataFrame, col_stats: Dict) -> List:
        """Greedy algorithm to order columns based on prefix preservation."""
        if len(df_subset.columns) <= 1:
            return list(df_subset.columns)
        
        columns = list(df_subset.columns)
        ordered = []
        remaining = set(columns)
        
        # Start with column that has lowest distinct ratio and highest frequency
        start_col = min(remaining, 
                       key=lambda x: (col_stats[x]['distinct_ratio'], 
                                     -col_stats[x]['most_common_freq']))
        ordered.append(start_col)
        remaining.remove(start_col)
        
        # Greedily add columns that maximize prefix matches
        while remaining:
            best_col = None
            best_score = -1
            
            for col in remaining:
                # Simulate adding this column next
                temp_order = ordered + [col]
                temp_df = df_subset[temp_order]
                
                # Compute quick estimate of prefix quality
                score = self._estimate_prefix_quality(temp_df, col_stats)
                
                if score > best_score:
                    best_score = score
                    best_col = col
            
            if best_col:
                ordered.append(best_col)
                remaining.remove(best_col)
            else:
                # Fallback: add any remaining column
                ordered.append(next(iter(remaining)))
                remaining.remove(ordered[-1])
        
        return ordered
    
    def _parallel_greedy_order(self, df_subset: pd.DataFrame, col_stats: Dict) -> List:
        """Parallel version of greedy column ordering."""
        n_workers = min(mp.cpu_count(), len(df_subset.columns))
        
        if n_workers <= 1:
            return self._greedy_column_order(df_subset, col_stats)
        
        columns = list(df_subset.columns)
        ordered = []
        remaining = set(columns)
        
        # Start column selection (serial)
        start_col = min(remaining,
                       key=lambda x: (col_stats[x]['distinct_ratio'],
                                     -col_stats[x]['most_common_freq']))
        ordered.append(start_col)
        remaining.remove(start_col)
        
        # Parallel greedy expansion
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            while remaining:
                futures = {}
                remaining_list = list(remaining)
                
                # Split work among workers
                chunk_size = max(1, len(remaining_list) // n_workers)
                chunks = [remaining_list[i:i + chunk_size] 
                         for i in range(0, len(remaining_list), chunk_size)]
                
                for chunk in chunks:
                    future = executor.submit(
                        self._evaluate_columns_chunk,
                        df_subset, ordered, chunk, col_stats
                    )
                    futures[future] = chunk
                
                # Collect results
                best_col = None
                best_score = -1
                
                for future in as_completed(futures):
                    chunk_results = future.result()
                    for col, score in chunk_results:
                        if score > best_score:
                            best_score = score
                            best_col = col
                
                if best_col:
                    ordered.append(best_col)
                    remaining.remove(best_col)
                else:
                    ordered.append(next(iter(remaining)))
                    remaining.remove(ordered[-1])
        
        return ordered
    
    def _evaluate_columns_chunk(self, df_subset: pd.DataFrame, ordered: List, 
                               chunk: List, col_stats: Dict) -> List[Tuple]:
        """Evaluate a chunk of columns for parallel processing."""
        results = []
        for col in chunk:
            temp_order = ordered + [col]
            temp_df = df_subset[temp_order]
            score = self._estimate_prefix_quality(temp_df, col_stats)
            results.append((col, score))
        return results
    
    def _estimate_prefix_quality(self, df: pd.DataFrame, col_stats: Dict) -> float:
        """Fast estimation of prefix quality without full computation."""
        # Sample rows for estimation
        n_samples = min(1000, len(df))
        if n_samples < 2:
            return 0
        
        sample_indices = np.random.choice(len(df), n_samples, replace=False)
        sample_df = df.iloc[sample_indices]
        
        # Convert to strings
        row_strings = sample_df.astype(str).agg(''.join, axis=1).tolist()
        
        # Compute prefix matches on sample
        total_lcp = 0
        prefixes = set()
        
        for i, s in enumerate(row_strings):
            if i == 0:
                prefixes.add(s)
                continue
            
            # Find LCP with existing prefixes
            max_lcp = 0
            for prefix_len in range(min(20, len(s)), 0, -1):
                prefix = s[:prefix_len]
                if prefix in prefixes:
                    max_lcp = prefix_len
                    break
            
            total_lcp += max_lcp
            prefixes.add(s)
        
        return total_lcp / (len(row_strings) - 1) if len(row_strings) > 1 else 0
    
    def _local_optimization(self, df: pd.DataFrame, initial_order: List, 
                           col_stats: Dict) -> List:
        """Apply local optimization using 2-opt swaps."""
        current_order = initial_order.copy()
        current_score = self._compute_hit_rate(df[current_order])
        
        improved = True
        max_iterations = 100
        
        for iteration in range(max_iterations):
            if not improved:
                break
            
            improved = False
            
            # Try swapping adjacent columns
            for i in range(len(current_order) - 1):
                new_order = current_order.copy()
                new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                
                # Quick estimation first
                est_score = self._estimate_prefix_quality(df[new_order], col_stats)
                if est_score <= current_score * 0.95:  # Threshold to avoid full computation
                    continue
                
                # Full computation if promising
                new_score = self._compute_hit_rate(df[new_order])
                
                if new_score > current_score:
                    current_order = new_order
                    current_score = new_score
                    improved = True
                    break
            
            # Try moving single column to different position
            if not improved and len(current_order) > 2:
                for i in range(len(current_order)):
                    for j in range(len(current_order)):
                        if i == j:
                            continue
                        
                        new_order = current_order.copy()
                        col = new_order.pop(i)
                        new_order.insert(j, col)
                        
                        est_score = self._estimate_prefix_quality(df[new_order], col_stats)
                        if est_score <= current_score * 0.95:
                            continue
                        
                        new_score = self._compute_hit_rate(df[new_order])
                        
                        if new_score > current_score:
                            current_order = new_order
                            current_score = new_score
                            improved = True
                            break
                    
                    if improved:
                        break
        
        return current_order

import pandas as pd
import numpy as np
from collections import defaultdict, deque
from typing import List, Tuple, Set, Dict, Optional
import heapq
import itertools
from concurrent.futures import ThreadPoolExecutor
import time

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
        if col_merge is not None:
            df = self._apply_column_merges(df, col_merge)
        
        # If dataframe is small, use brute force
        if len(df.columns) <= 10:
            return self._brute_force_optimize(df)
        
        # Use heuristic optimization for larger datasets
        return self._heuristic_optimize(
            df, early_stop, row_stop, col_stop, 
            distinct_value_threshold, parallel
        )
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Merge columns as specified in col_merge list."""
        result_df = df.copy()
        merged_cols = set()
        
        for i, merge_group in enumerate(col_merge):
            if not merge_group:
                continue
                
            # Get columns to merge
            cols_to_merge = [col for col in merge_group if col in result_df.columns]
            if not cols_to_merge:
                continue
                
            # Create merged column
            merged_name = f"merged_{i}"
            merged_series = df[cols_to_merge[0]].astype(str)
            for col in cols_to_merge[1:]:
                merged_series += df[col].astype(str)
            
            # Add merged column and mark original columns for removal
            result_df[merged_name] = merged_series
            merged_cols.update(cols_to_merge)
        
        # Remove original merged columns
        cols_to_keep = [col for col in result_df.columns if col not in merged_cols]
        return result_df[cols_to_keep]
    
    def _brute_force_optimize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Brute force optimization for small number of columns."""
        cols = list(df.columns)
        n_cols = len(cols)
        
        # Try all permutations for n <= 6, otherwise sample
        if n_cols <= 6:
            permutations = list(itertools.permutations(cols))
        else:
            # Sample permutations using heuristic
            permutations = self._generate_permutation_samples(cols, 1000)
        
        best_order = cols
        best_score = self._compute_hit_rate(df[cols])
        
        for perm in permutations:
            score = self._compute_hit_rate(df[list(perm)])
            if score > best_score:
                best_score = score
                best_order = list(perm)
        
        return df[best_order]
    
    def _heuristic_optimize(
        self, df: pd.DataFrame, early_stop: int, row_stop: int, 
        col_stop: int, distinct_value_threshold: float, parallel: bool
    ) -> pd.DataFrame:
        """Heuristic optimization for larger datasets."""
        cols = list(df.columns)
        n_cols = len(cols)
        
        # Phase 1: Greedy construction with multiple seeds
        seeds = self._generate_seeds(df, cols, distinct_value_threshold)
        candidates = []
        
        for seed in seeds:
            order = self._greedy_construct(df, seed, row_stop)
            score = self._compute_hit_rate(df[order])
            candidates.append((score, order))
        
        # Phase 2: Local search
        improved_candidates = []
        for score, order in candidates:
            improved_order = self._local_search(df, order, col_stop, early_stop)
            improved_score = self._compute_hit_rate(df[improved_order])
            improved_candidates.append((improved_score, improved_order))
        
        # Phase 3: Merge best orders
        best_score, best_order = max(improved_candidates, key=lambda x: x[0])
        
        # Try recombination if we have multiple good candidates
        if len(improved_candidates) >= 2:
            top_candidates = [order for _, order in heapq.nlargest(
                min(3, len(improved_candidates)), improved_candidates
            )]
            recombined = self._recombine_orders(df, top_candidates)
            recombined_score = self._compute_hit_rate(df[recombined])
            
            if recombined_score > best_score:
                best_score = recombined_score
                best_order = recombined
        
        return df[best_order]
    
    def _generate_seeds(
        self, df: pd.DataFrame, cols: List[str], distinct_threshold: float
    ) -> List[List[str]]:
        """Generate initial seed permutations using different strategies."""
        seeds = []
        
        # Strategy 1: Sort by column distinctiveness (lowest first)
        distinct_counts = []
        for col in cols:
            distinct_ratio = df[col].nunique() / len(df)
            if distinct_ratio <= distinct_threshold:
                priority = distinct_ratio
            else:
                priority = 1.0 + (1.0 - 1.0/(1.0 + distinct_ratio))
            distinct_counts.append((priority, col))
        
        distinct_counts.sort(key=lambda x: x[0])
        seeds.append([col for _, col in distinct_counts])
        
        # Strategy 2: Sort by column correlation
        if len(cols) > 1:
            correlated_order = self._get_correlated_order(df, cols)
            seeds.append(correlated_order)
        
        # Strategy 3: Reverse of strategy 1
        seeds.append(list(reversed(seeds[0])))
        
        # Strategy 4: Random permutations (up to 5)
        n_seeds = min(5, len(cols))
        for _ in range(n_seeds):
            perm = cols.copy()
            np.random.shuffle(perm)
            seeds.append(perm)
        
        return seeds
    
    def _get_correlated_order(self, df: pd.DataFrame, cols: List[str]) -> List[str]:
        """Order columns by pairwise correlation."""
        n = len(cols)
        if n <= 1:
            return cols
        
        # Convert to string and compute approximate correlations
        correlations = np.zeros((n, n))
        
        # Sample rows for efficiency
        sample_size = min(1000, len(df))
        if sample_size < len(df):
            sample_df = df.sample(sample_size, random_state=42)
        else:
            sample_df = df
        
        # Compute string-based similarity
        for i in range(n):
            col_i = sample_df[cols[i]].astype(str).values
            for j in range(i + 1, n):
                col_j = sample_df[cols[j]].astype(str).values
                # Simple matching coefficient
                matches = np.sum(col_i == col_j)
                sim = matches / sample_size
                correlations[i, j] = sim
                correlations[j, i] = sim
        
        # Greedy ordering based on average similarity
        visited = set()
        order = []
        
        # Start with column having highest average similarity
        avg_sim = np.mean(correlations, axis=1)
        current = np.argmax(avg_sim)
        visited.add(current)
        order.append(cols[current])
        
        while len(visited) < n:
            best_next = -1
            best_sim = -1
            
            for j in range(n):
                if j not in visited:
                    sim = correlations[current, j]
                    if sim > best_sim:
                        best_sim = sim
                        best_next = j
            
            if best_next == -1:
                # Add any unvisited column
                for j in range(n):
                    if j not in visited:
                        best_next = j
                        break
            
            if best_next != -1:
                current = best_next
                visited.add(current)
                order.append(cols[current])
        
        return order
    
    def _greedy_construct(
        self, df: pd.DataFrame, initial_order: List[str], row_stop: int
    ) -> List[str]:
        """Greedy construction of column order."""
        remaining = set(initial_order)
        order = []
        
        # Sample rows for efficiency
        sample_size = min(row_stop * 100, len(df))
        if sample_size < len(df):
            sample_df = df.sample(sample_size, random_state=42)
        else:
            sample_df = df
        
        while remaining:
            if len(order) == 0:
                # Choose column with most common prefixes
                best_col = self._choose_initial_column(sample_df, list(remaining))
                order.append(best_col)
                remaining.remove(best_col)
            else:
                # Choose next column that maximizes prefix matches
                best_col = None
                best_gain = -1
                
                for col in remaining:
                    test_order = order + [col]
                    gain = self._estimate_gain(sample_df, order, test_order)
                    
                    if gain > best_gain:
                        best_gain = gain
                        best_col = col
                
                if best_col:
                    order.append(best_col)
                    remaining.remove(best_col)
                else:
                    # Add any remaining column
                    order.append(next(iter(remaining)))
                    remaining.remove(order[-1])
        
        return order
    
    def _choose_initial_column(
        self, df: pd.DataFrame, cols: List[str]
    ) -> str:
        """Choose initial column based on prefix stability."""
        best_col = cols[0]
        best_score = -1
        
        for col in cols:
            # Score based on early row similarity
            values = df[col].astype(str).values
            if len(values) > 0:
                first_val = values[0]
                matches = np.sum(values == first_val)
                score = matches / len(values)
                
                if score > best_score:
                    best_score = score
                    best_col = col
        
        return best_col
    
    def _estimate_gain(
        self, df: pd.DataFrame, current_order: List[str], new_order: List[str]
    ) -> float:
        """Estimate gain from adding a column."""
        if len(current_order) == 0:
            return 0.0
        
        # Use small sample for estimation
        sample_size = min(100, len(df))
        sample_indices = np.random.choice(len(df), sample_size, replace=False)
        
        current_strings = []
        new_strings = []
        
        for idx in sample_indices:
            row = df.iloc[idx]
            current_str = ''.join(str(row[col]) for col in current_order)
            new_str = ''.join(str(row[col]) for col in new_order)
            current_strings.append(current_str)
            new_strings.append(new_str)
        
        # Compute approximate hit rate improvement
        current_hits = self._compute_sample_hit_rate(current_strings)
        new_hits = self._compute_sample_hit_rate(new_strings)
        
        return new_hits - current_hits
    
    def _compute_sample_hit_rate(self, strings: List[str]) -> float:
        """Compute hit rate for a sample of strings."""
        if len(strings) <= 1:
            return 0.0
        
        total_lcp = 0
        total_len = sum(len(s) for s in strings)
        
        for i in range(1, len(strings)):
            max_lcp = 0
            for j in range(i):
                lcp = 0
                s1, s2 = strings[i], strings[j]
                min_len = min(len(s1), len(s2))
                while lcp < min_len and s1[lcp] == s2[lcp]:
                    lcp += 1
                max_lcp = max(max_lcp, lcp)
            total_lcp += max_lcp
        
        return total_lcp / total_len if total_len > 0 else 0.0
    
    def _local_search(
        self, df: pd.DataFrame, initial_order: List[str], 
        col_stop: int, early_stop: int
    ) -> List[str]:
        """Local search optimization."""
        current_order = initial_order.copy()
        current_score = self._compute_hit_rate(df[current_order])
        n_cols = len(current_order)
        
        improved = True
        iterations = 0
        
        while improved and iterations < early_stop:
            improved = False
            
            # Try column swaps
            for i in range(n_cols):
                for j in range(i + 1, min(i + col_stop + 1, n_cols)):
                    iterations += 1
                    if iterations >= early_stop:
                        break
                    
                    # Try swap
                    new_order = current_order.copy()
                    new_order[i], new_order[j] = new_order[j], new_order[i]
                    
                    # Quick evaluation
                    quick_score = self._quick_evaluate(df, new_order, current_score)
                    
                    if quick_score > current_score:
                        # Full evaluation
                        new_score = self._compute_hit_rate(df[new_order])
                        if new_score > current_score:
                            current_order = new_order
                            current_score = new_score
                            improved = True
                            break
                
                if improved:
                    break
        
        return current_order
    
    def _quick_evaluate(
        self, df: pd.DataFrame, order: List[str], baseline: float
    ) -> float:
        """Quick evaluation of candidate order."""
        # Use small sample for quick evaluation
        sample_size = min(500, len(df))
        if sample_size < len(df):
            sample_df = df.sample(sample_size, random_state=42)
        else:
            sample_df = df
        
        return self._compute_hit_rate(sample_df[order])
    
    def _recombine_orders(
        self, df: pd.DataFrame, orders: List[List[str]]
    ) -> List[str]:
        """Recombine multiple good orders."""
        if len(orders) <= 1:
            return orders[0] if orders else []
        
        # Use order crossover
        n_cols = len(orders[0])
        result = orders[0].copy()
        
        # Try combining segments from different orders
        segment_size = max(2, n_cols // 3)
        
        for start in range(0, n_cols, segment_size):
            end = min(start + segment_size, n_cols)
            
            # Try each order for this segment
            best_segment = result[start:end]
            best_score = self._compute_hit_rate(df[result])
            
            for order in orders[1:]:
                if len(order) == n_cols:
                    test_order = result.copy()
                    test_order[start:end] = order[start:end]
                    
                    # Ensure all columns are present
                    if len(set(test_order)) == n_cols:
                        score = self._compute_hit_rate(df[test_order])
                        if score > best_score:
                            best_score = score
                            best_segment = order[start:end]
            
            result[start:end] = best_segment
        
        return result
    
    def _generate_permutation_samples(
        self, cols: List[str], n_samples: int
    ) -> List[Tuple[str]]:
        """Generate permutation samples for brute force."""
        samples = []
        n_cols = len(cols)
        
        # Add original order
        samples.append(tuple(cols))
        
        # Add reversed order
        samples.append(tuple(reversed(cols)))
        
        # Add variations based on distinctiveness
        for _ in range(min(n_samples - 2, 100)):
            weights = np.random.rand(n_cols)
            perm = [col for _, col in sorted(zip(weights, cols), reverse=True)]
            samples.append(tuple(perm))
        
        return list(set(samples))
    
    def _compute_hit_rate(self, df: pd.DataFrame) -> float:
        """Compute the actual hit rate for a given column order."""
        n_rows = len(df)
        if n_rows <= 1:
            return 0.0
        
        # Convert to strings row by row
        strings = []
        total_len = 0
        
        for _, row in df.iterrows():
            row_str = ''.join(str(val) for val in row)
            strings.append(row_str)
            total_len += len(row_str)
        
        # Compute LCP sum
        total_lcp = 0
        
        for i in range(1, n_rows):
            max_lcp = 0
            s1 = strings[i]
            
            for j in range(i):
                s2 = strings[j]
                lcp = 0
                min_len = min(len(s1), len(s2))
                
                # Compare character by character
                while lcp < min_len and s1[lcp] == s2[lcp]:
                    lcp += 1
                
                max_lcp = max(max_lcp, lcp)
            
            total_lcp += max_lcp
        
        return total_lcp / total_len if total_len > 0 else 0.0
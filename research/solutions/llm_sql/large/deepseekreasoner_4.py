import pandas as pd
import numpy as np
from collections import defaultdict
import itertools
import math
from typing import List, Tuple
import random

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
        
        # Get column order that maximizes prefix hit rate
        best_order = self._optimize_column_order(
            df, early_stop, row_stop, col_stop, 
            distinct_value_threshold, parallel
        )
        
        # Reorder columns
        return df[best_order]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Merge specified columns into single columns."""
        new_df = df.copy()
        columns_to_drop = []
        
        for merge_group in col_merge:
            if not merge_group:
                continue
                
            # Use first column name as the merged column name
            new_col_name = merge_group[0]
            
            # Concatenate values from all columns in the group
            def merge_row(row):
                return ''.join(str(row[col]) for col in merge_group if col in row)
            
            new_df[new_col_name] = new_df.apply(merge_row, axis=1)
            
            # Mark columns for removal (except the first one which we're reusing)
            columns_to_drop.extend([col for col in merge_group[1:] if col in new_df])
        
        # Remove the old columns
        new_df = new_df.drop(columns=[col for col in columns_to_drop if col in new_df])
        return new_df
    
    def _optimize_column_order(
        self, 
        df: pd.DataFrame,
        early_stop: int,
        row_stop: int,
        col_stop: int,
        distinct_value_threshold: float,
        parallel: bool
    ) -> List[str]:
        """Find optimal column order to maximize prefix hit rate."""
        
        n_rows, n_cols = df.shape
        col_names = list(df.columns)
        
        if n_cols <= 1:
            return col_names
        
        # Calculate column statistics
        col_stats = self._calculate_column_stats(df, distinct_value_threshold)
        
        # Use different strategies based on problem size
        if n_cols <= 10:
            return self._exact_search(df, col_names, col_stats, early_stop)
        elif n_cols <= 20:
            return self._beam_search(df, col_names, col_stats, early_stop, row_stop)
        else:
            return self._greedy_optimization(df, col_names, col_stats, early_stop, col_stop)
    
    def _calculate_column_stats(self, df: pd.DataFrame, threshold: float) -> dict:
        """Calculate statistics for each column."""
        stats = {}
        n_rows = len(df)
        
        for col in df.columns:
            col_data = df[col].astype(str)
            unique_count = col_data.nunique()
            unique_ratio = unique_count / n_rows
            
            # Calculate prefix distribution
            prefix_dict = defaultdict(int)
            for val in col_data:
                if len(val) > 0:
                    prefix_dict[val[0]] += 1
            
            # Calculate prefix entropy
            prefix_entropy = 0
            for count in prefix_dict.values():
                p = count / n_rows
                prefix_entropy -= p * math.log2(p + 1e-10)
            
            stats[col] = {
                'unique_ratio': unique_ratio,
                'prefix_entropy': prefix_entropy,
                'is_low_cardinality': unique_ratio <= threshold,
                'nunique': unique_count
            }
        
        return stats
    
    def _exact_search(self, df: pd.DataFrame, col_names: List[str], 
                     col_stats: dict, early_stop: int) -> List[str]:
        """Exact search for small number of columns."""
        best_order = col_names
        best_score = self._calculate_hit_rate(df[best_order])
        
        # Try all permutations for small column counts
        if len(col_names) <= 8:
            for perm in itertools.permutations(col_names):
                current_score = self._calculate_hit_rate(df[list(perm)])
                if current_score > best_score:
                    best_score = current_score
                    best_order = list(perm)
        
        return best_order
    
    def _beam_search(self, df: pd.DataFrame, col_names: List[str],
                    col_stats: dict, early_stop: int, beam_width: int) -> List[str]:
        """Beam search for moderate number of columns."""
        # Sort columns by cardinality (low cardinality first)
        sorted_cols = sorted(col_names, 
                           key=lambda x: (col_stats[x]['nunique'], 
                                        -col_stats[x]['prefix_entropy']))
        
        beam = [(0, [])]  # (score, ordering)
        
        for i, col in enumerate(sorted_cols):
            new_beam = []
            
            for score, ordering in beam:
                # Try inserting column at each position
                for pos in range(len(ordering) + 1):
                    new_ordering = ordering.copy()
                    new_ordering.insert(pos, col)
                    
                    if len(new_ordering) <= 10:  # Limit evaluation depth
                        partial_df = df[new_ordering]
                        new_score = self._calculate_hit_rate(partial_df)
                    else:
                        # Use heuristic for longer orderings
                        new_score = score + (1.0 / (i + 1))
                    
                    new_beam.append((new_score, new_ordering))
            
            # Keep top beam_width candidates
            new_beam.sort(reverse=True, key=lambda x: x[0])
            beam = new_beam[:beam_width]
            
            if len(beam[0][1]) == len(sorted_cols):
                break
        
        return max(beam, key=lambda x: x[0])[1]
    
    def _greedy_optimization(self, df: pd.DataFrame, col_names: List[str],
                           col_stats: dict, early_stop: int, col_stop: int) -> List[str]:
        """Greedy optimization for large number of columns."""
        
        # Start with columns sorted by low cardinality and high prefix similarity
        current_order = self._get_initial_order(col_names, col_stats)
        best_order = current_order.copy()
        best_score = self._calculate_hit_rate(df[best_order])
        
        n_cols = len(col_names)
        iterations = 0
        
        while iterations < early_stop:
            improved = False
            
            # Try swapping adjacent columns
            for i in range(n_cols - 1):
                new_order = current_order.copy()
                new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                
                new_score = self._calculate_hit_rate(df[new_order])
                
                if new_score > best_score:
                    best_score = new_score
                    best_order = new_order.copy()
                    current_order = new_order.copy()
                    improved = True
                    break
            
            # Try moving low cardinality columns forward
            if not improved:
                low_card_cols = [col for col in current_order 
                               if col_stats[col]['is_low_cardinality']]
                
                if len(low_card_cols) > 1:
                    for i, col in enumerate(low_card_cols[1:], 1):
                        new_order = current_order.copy()
                        current_idx = new_order.index(col)
                        target_idx = new_order.index(low_card_cols[i-1])
                        
                        if current_idx > target_idx:
                            new_order.pop(current_idx)
                            new_order.insert(target_idx, col)
                            
                            new_score = self._calculate_hit_rate(df[new_order])
                            
                            if new_score > best_score:
                                best_score = new_score
                                best_order = new_order.copy()
                                current_order = new_order.copy()
                                improved = True
                                break
            
            iterations += 1
            
            if not improved:
                # Random perturbation to escape local optimum
                if iterations % 10 == 0:
                    idx1, idx2 = random.sample(range(n_cols), 2)
                    current_order[idx1], current_order[idx2] = current_order[idx2], current_order[idx1]
        
        return best_order
    
    def _get_initial_order(self, col_names: List[str], col_stats: dict) -> List[str]:
        """Get initial column ordering based on statistics."""
        
        # Group columns by cardinality
        low_card_cols = [col for col in col_names 
                        if col_stats[col]['is_low_cardinality']]
        high_card_cols = [col for col in col_names 
                         if not col_stats[col]['is_low_cardinality']]
        
        # Sort low cardinality columns by prefix entropy (low entropy first)
        low_card_cols.sort(key=lambda x: (col_stats[x]['prefix_entropy'], 
                                        col_stats[x]['nunique']))
        
        # Sort high cardinality columns by unique ratio
        high_card_cols.sort(key=lambda x: col_stats[x]['unique_ratio'])
        
        return low_card_cols + high_card_cols
    
    def _calculate_hit_rate(self, df: pd.DataFrame) -> float:
        """Calculate prefix hit rate for the given column order."""
        n_rows = len(df)
        
        if n_rows <= 1:
            return 0.0
        
        # Convert rows to strings
        row_strings = []
        total_length = 0
        
        for _, row in df.iterrows():
            row_str = ''.join(str(val) for val in row)
            row_strings.append(row_str)
            total_length += len(row_str)
        
        if total_length == 0:
            return 0.0
        
        # Calculate total LCP
        total_lcp = 0
        seen_prefixes = {}
        
        for i in range(n_rows):
            current_str = row_strings[i]
            best_lcp = 0
            
            # Check against previous rows
            for j in range(i):
                prev_str = row_strings[j]
                lcp = 0
                min_len = min(len(current_str), len(prev_str))
                
                while lcp < min_len and current_str[lcp] == prev_str[lcp]:
                    lcp += 1
                
                if lcp > best_lcp:
                    best_lcp = lcp
            
            total_lcp += best_lcp
        
        return total_lcp / total_length
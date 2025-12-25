import pandas as pd
import numpy as np
from collections import defaultdict
import time
from typing import List, Tuple
import itertools
from functools import lru_cache

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
        
        start_time = time.time()
        
        # Apply column merges if specified
        if col_merge is not None and len(col_merge) > 0:
            df = self._apply_column_merges(df, col_merge)
        
        # If 1 or 0 columns, return as is
        if len(df.columns) <= 1:
            return df
        
        # Get column names
        columns = list(df.columns)
        n_cols = len(columns)
        
        # Convert all values to strings
        df_str = df.astype(str)
        
        # Precompute column data
        col_data = {}
        for col in columns:
            col_data[col] = df_str[col].values
        
        # Analyze column characteristics
        col_stats = self._analyze_columns(col_data, df_str)
        
        # Generate candidate permutations
        candidates = self._generate_candidates(columns, col_stats, n_cols, 
                                             early_stop, col_stop, distinct_value_threshold)
        
        # Evaluate candidates
        best_order = None
        best_score = -1
        
        for order in candidates:
            if time.time() - start_time > 9.5:  # Leave 0.5s buffer
                break
                
            score = self._evaluate_order(order, col_data, df_str.shape[0], row_stop)
            
            if score > best_score:
                best_score = score
                best_order = order
        
        # If no order found (shouldn't happen), use original
        if best_order is None:
            best_order = columns
        
        # Return reordered dataframe
        return df[best_order]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Apply column merges as specified."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if not merge_group:
                continue
                
            # Get the columns to merge
            merge_cols = [col for col in merge_group if col in result_df.columns]
            if len(merge_cols) <= 1:
                continue
            
            # Create merged column
            merged_name = merge_cols[0] + "_merged"
            merged_values = result_df[merge_cols[0]].astype(str)
            
            for col in merge_cols[1:]:
                merged_values = merged_values + result_df[col].astype(str)
            
            # Add merged column and remove original columns
            result_df[merged_name] = merged_values
            result_df = result_df.drop(columns=merge_cols)
        
        return result_df
    
    def _analyze_columns(self, col_data: dict, df_str: pd.DataFrame) -> dict:
        """Analyze column statistics for better ordering."""
        n_rows = len(next(iter(col_data.values())))
        stats = {}
        
        for col, values in col_data.items():
            # Calculate distinct ratio
            unique_values = len(set(values))
            distinct_ratio = unique_values / n_rows
            
            # Calculate average string length
            avg_len = sum(len(str(v)) for v in values) / n_rows
            
            # Calculate prefix stability (how often values start with same char)
            first_chars = [str(v)[0] if len(str(v)) > 0 else '' for v in values]
            unique_first = len(set(first_chars))
            first_char_stability = (n_rows - unique_first) / n_rows if n_rows > 0 else 0
            
            stats[col] = {
                'distinct_ratio': distinct_ratio,
                'avg_len': avg_len,
                'first_char_stability': first_char_stability,
                'unique_count': unique_values
            }
        
        return stats
    
    def _generate_candidates(self, columns: List[str], col_stats: dict, 
                           n_cols: int, early_stop: int, col_stop: int,
                           distinct_value_threshold: float) -> List[List[str]]:
        """Generate candidate column orderings."""
        candidates = []
        
        # 1. Original order (baseline)
        candidates.append(columns.copy())
        
        # 2. Sort by distinct ratio (lowest first) - more repeating values first
        sorted_by_distinct = sorted(columns, 
                                   key=lambda x: col_stats[x]['distinct_ratio'])
        if sorted_by_distinct != columns:
            candidates.append(sorted_by_distinct)
        
        # 3. Sort by first character stability (highest first)
        sorted_by_stability = sorted(columns, 
                                    key=lambda x: -col_stats[x]['first_char_stability'])
        if sorted_by_stability != columns:
            candidates.append(sorted_by_stability)
        
        # 4. Sort by average length (shortest first) - shorter prefixes first
        sorted_by_length = sorted(columns, 
                                 key=lambda x: col_stats[x]['avg_len'])
        if sorted_by_length != columns:
            candidates.append(sorted_by_length)
        
        # 5. Composite score: prioritize low distinct ratio and high stability
        def composite_score(col):
            stats = col_stats[col]
            # Weight distinct ratio more heavily
            return (0.7 * (1 - stats['distinct_ratio']) + 
                    0.3 * stats['first_char_stability'])
        
        sorted_by_composite = sorted(columns, key=composite_score, reverse=True)
        if sorted_by_composite != columns:
            candidates.append(sorted_by_composite)
        
        # 6. Generate additional permutations for small number of columns
        if n_cols <= 6:
            # Generate all permutations for small n (max 720 for n=6)
            all_perms = list(itertools.permutations(columns))
            # Add a few more random permutations
            for perm in all_perms[:min(20, len(all_perms))]:
                if list(perm) not in candidates:
                    candidates.append(list(perm))
        else:
            # For larger n, use heuristic swaps
            base_order = sorted_by_composite
            
            # Generate variations by swapping adjacent pairs
            for i in range(min(n_cols-1, 10)):
                new_order = base_order.copy()
                new_order[i], new_order[i+1] = new_order[i+1], new_order[i]
                if new_order not in candidates:
                    candidates.append(new_order)
            
            # Generate variations by moving low-distinct columns to front
            low_distinct_cols = [c for c in columns 
                                if col_stats[c]['distinct_ratio'] < distinct_value_threshold]
            high_distinct_cols = [c for c in columns 
                                 if c not in low_distinct_cols]
            
            if low_distinct_cols and high_distinct_cols:
                new_order = low_distinct_cols + high_distinct_cols
                if new_order not in candidates:
                    candidates.append(new_order)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for cand in candidates:
            cand_tuple = tuple(cand)
            if cand_tuple not in seen:
                seen.add(cand_tuple)
                unique_candidates.append(cand)
        
        return unique_candidates[:early_stop]
    
    def _evaluate_order(self, order: List[str], col_data: dict, 
                       n_rows: int, row_stop: int) -> float:
        """Evaluate a column ordering by calculating prefix hit rate."""
        if n_rows <= 1:
            return 0.0
        
        # Use all rows for evaluation (row_stop seems to be misnamed parameter)
        sample_size = n_rows
        
        # Build prefix tree for fast LCP calculation
        prefix_tree = {}
        total_lcp = 0
        total_len = 0
        
        for i in range(sample_size):
            # Build string for current row in given order
            row_str = ''.join(str(col_data[col][i]) for col in order)
            row_len = len(row_str)
            total_len += row_len
            
            if i == 0:
                # Insert first row into prefix tree
                node = prefix_tree
                for char in row_str:
                    if char not in node:
                        node[char] = {}
                    node = node[char]
                continue
            
            # Find LCP with previous rows using prefix tree
            node = prefix_tree
            lcp = 0
            for char in row_str:
                if char in node:
                    lcp += 1
                    node = node[char]
                else:
                    break
            
            total_lcp += lcp
            
            # Insert current row into prefix tree
            node = prefix_tree
            for char in row_str:
                if char not in node:
                    node[char] = {}
                node = node[char]
        
        if total_len == 0:
            return 0.0
        
        return total_lcp / total_len

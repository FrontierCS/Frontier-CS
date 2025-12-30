import pandas as pd
import random
import itertools
from collections import defaultdict
import time
import math
from typing import List, Tuple, Optional
import multiprocessing as mp
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
        # Apply column merges if specified
        if col_merge is not None:
            df = self._apply_column_merges(df, col_merge)
        
        # If only one column, return as is
        if df.shape[1] <= 1:
            return df
        
        # Prepare data for optimization
        column_data = self._preprocess_columns(df)
        n_rows, n_cols = df.shape
        
        # Determine sample size for evaluation
        sample_size = min(row_stop, n_rows) if row_stop > 0 else n_rows
        
        # Generate sample indices (preserving order)
        if sample_size < n_rows:
            step = max(1, n_rows // sample_size)
            sample_indices = list(range(0, n_rows, step))[:sample_size]
        else:
            sample_indices = list(range(n_rows))
        
        # Precompute column strings for sample rows
        col_strings = []
        for col in df.columns:
            col_vals = df[col].astype(str).values
            sample_vals = [col_vals[i] for i in sample_indices]
            col_strings.append(sample_vals)
        
        # Calculate column statistics for heuristics
        col_stats = self._compute_column_stats(df, distinct_value_threshold)
        
        # Find best permutation using beam search with early stopping
        best_perm = self._beam_search_optimize(
            col_strings, col_stats, n_cols, early_stop, col_stop, parallel
        )
        
        # Reorder columns according to best permutation
        col_names = list(df.columns)
        ordered_cols = [col_names[i] for i in best_perm]
        return df[ordered_cols]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Merge columns as specified in col_merge groups."""
        df = df.copy()
        for group in col_merge:
            if len(group) < 2:
                continue
            # Use first column as the merged column
            main_col = group[0]
            # Concatenate values without spaces
            merged_vals = df[group].apply(
                lambda row: ''.join(row.astype(str)), axis=1
            )
            df[main_col] = merged_vals
            # Remove the other columns in the group
            cols_to_drop = [col for col in group if col != main_col]
            df = df.drop(columns=cols_to_drop)
        return df
    
    def _preprocess_columns(self, df: pd.DataFrame) -> List[List[str]]:
        """Convert each column to list of string values."""
        return [df[col].astype(str).tolist() for col in df.columns]
    
    def _compute_column_stats(self, df: pd.DataFrame, threshold: float) -> List[dict]:
        """Compute statistics for each column to guide search."""
        stats = []
        for col in df.columns:
            col_vals = df[col].astype(str)
            unique_vals = col_vals.nunique()
            total = len(col_vals)
            distinct_ratio = unique_vals / total
            
            # Average string length
            avg_len = col_vals.str.len().mean()
            
            # Prefix commonality: average length of common prefix with next row
            prefix_sum = 0
            for i in range(total - 1):
                s1, s2 = col_vals.iloc[i], col_vals.iloc[i+1]
                prefix_len = 0
                min_len = min(len(s1), len(s2))
                while prefix_len < min_len and s1[prefix_len] == s2[prefix_len]:
                    prefix_len += 1
                prefix_sum += prefix_len
            avg_prefix = prefix_sum / (total - 1) if total > 1 else 0
            
            stats.append({
                'distinct_ratio': distinct_ratio,
                'avg_len': avg_len,
                'avg_prefix': avg_prefix,
                'score': (1 - distinct_ratio) * avg_len + avg_prefix
            })
        return stats
    
    def _evaluate_permutation(
        self, perm: Tuple[int], col_strings: List[List[str]]
    ) -> float:
        """Calculate hit rate for a given column permutation on sample data."""
        n_samples = len(col_strings[0])
        if n_samples <= 1:
            return 0.0
        
        total_lcp = 0
        total_len = 0
        trie = {}
        
        for i in range(n_samples):
            # Build concatenated string for this row
            row_str = ''.join(col_strings[c][i] for c in perm)
            row_len = len(row_str)
            total_len += row_len
            
            if i == 0:
                # First row, no previous rows to compare
                pass
            else:
                # Find longest common prefix with any previous row
                node = trie
                lcp = 0
                for ch in row_str:
                    if ch in node:
                        lcp += 1
                        node = node[ch]
                    else:
                        break
                total_lcp += lcp
            
            # Insert current row into trie
            node = trie
            for ch in row_str:
                if ch not in node:
                    node[ch] = {}
                node = node[ch]
        
        return total_lcp / total_len if total_len > 0 else 0.0
    
    def _beam_search_optimize(
        self,
        col_strings: List[List[str]],
        col_stats: List[dict],
        n_cols: int,
        early_stop: int,
        beam_width: int,
        parallel: bool
    ) -> List[int]:
        """Beam search for best column permutation."""
        # Initialize with empty permutation
        beam = [([], 0.0)]
        evaluated = 0
        
        # Precompute column scores for ordering
        col_scores = [(i, col_stats[i]['score']) for i in range(n_cols)]
        col_scores.sort(key=lambda x: x[1], reverse=True)
        col_order = [i for i, _ in col_scores]
        
        # Use caching for evaluated permutations
        @lru_cache(maxsize=10000)
        def cached_evaluate(perm_tuple):
            return self._evaluate_permutation(perm_tuple, col_strings)
        
        for depth in range(n_cols):
            new_beam = []
            for perm, score in beam:
                used = set(perm)
                for col in col_order:
                    if col in used:
                        continue
                    new_perm = tuple(perm + [col])
                    
                    # Evaluate the new permutation
                    new_score = cached_evaluate(new_perm)
                    evaluated += 1
                    
                    new_beam.append((list(new_perm), new_score))
                    
                    # Early stopping if we've evaluated enough permutations
                    if evaluated >= early_stop:
                        break
                
                if evaluated >= early_stop:
                    break
            
            if not new_beam:
                break
            
            # Sort by score and keep top beam_width
            new_beam.sort(key=lambda x: x[1], reverse=True)
            beam = new_beam[:beam_width]
            
            if evaluated >= early_stop:
                break
        
        # Return best permutation found
        if beam:
            best_perm, best_score = max(beam, key=lambda x: x[1])
            return best_perm
        
        # Fallback: return original order
        return list(range(n_cols))
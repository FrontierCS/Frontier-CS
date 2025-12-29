import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Set
from collections import defaultdict
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
        
        # Apply column merges first
        if col_merge:
            df = self._apply_column_merges(df, col_merge)
        
        # If no columns left after merge, return empty dataframe
        if len(df.columns) == 0:
            return df
        
        # Get original column order
        original_cols = list(df.columns)
        
        # Convert all values to strings
        df_str = df.astype(str)
        
        # Analyze column statistics
        col_stats = self._analyze_columns(df_str)
        
        # Get column ordering using heuristic algorithm
        best_order = self._optimize_column_order(
            df_str, col_stats, 
            early_stop, row_stop, col_stop,
            distinct_value_threshold
        )
        
        # Apply the best column order
        return df[best_order]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Apply column merges as specified."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if not merge_group:
                continue
                
            # Check if all columns in the group exist
            existing_cols = [col for col in merge_group if col in result_df.columns]
            if len(existing_cols) < 2:
                continue
                
            # Create merged column
            merged_name = existing_cols[0] + "_merged"
            result_df[merged_name] = result_df[existing_cols].astype(str).apply(
                lambda row: ''.join(row), axis=1
            )
            
            # Remove original columns
            result_df = result_df.drop(columns=existing_cols)
        
        return result_df
    
    def _analyze_columns(self, df: pd.DataFrame) -> Dict:
        """Analyze column statistics for heuristic ordering."""
        col_stats = {}
        n_rows = len(df)
        
        for col in df.columns:
            col_data = df[col]
            # Unique values and frequency
            value_counts = col_data.value_counts()
            n_unique = len(value_counts)
            
            # Common prefix analysis within column
            if n_unique < n_rows:
                # Find most common value
                most_common = value_counts.index[0]
                # Calculate average prefix match with most common value
                prefix_matches = col_data.apply(
                    lambda x: self._lcp_length(str(x), str(most_common))
                ).mean()
            else:
                prefix_matches = 0
            
            # String length statistics
            str_lengths = col_data.str.len()
            avg_len = str_lengths.mean()
            
            col_stats[col] = {
                'n_unique': n_unique,
                'unique_ratio': n_unique / n_rows,
                'prefix_matches': prefix_matches,
                'avg_length': avg_len,
                'density': 1.0 if n_unique == 1 else (n_rows - n_unique) / (n_rows - 1)
            }
        
        return col_stats
    
    def _optimize_column_order(
        self, 
        df: pd.DataFrame, 
        col_stats: Dict,
        early_stop: int,
        row_stop: int,
        col_stop: int,
        distinct_value_threshold: float
    ) -> List[str]:
        """Optimize column order using heuristic approach."""
        n_cols = len(df.columns)
        all_cols = list(df.columns)
        
        if n_cols <= 1:
            return all_cols
        
        # Sort columns by heuristic criteria
        sorted_cols = self._initial_column_sort(all_cols, col_stats, distinct_value_threshold)
        
        # Try beam search with limited permutations
        best_order, best_score = self._beam_search(
            df, sorted_cols, col_stats,
            beam_width=min(50, early_stop // 100),
            max_iterations=min(1000, early_stop)
        )
        
        return best_order
    
    def _initial_column_sort(
        self, 
        cols: List[str], 
        col_stats: Dict,
        threshold: float
    ) -> List[str]:
        """Initial sort of columns based on heuristics."""
        # Group columns by their characteristics
        high_density = []
        medium_density = []
        low_density = []
        
        for col in cols:
            stats = col_stats[col]
            if stats['density'] >= 0.8:  # Very high density (mostly same values)
                high_density.append(col)
            elif stats['density'] >= 0.3:  # Medium density
                medium_density.append(col)
            else:  # Low density
                low_density.append(col)
        
        # Sort within groups
        def sort_key(col):
            stats = col_stats[col]
            # Prefer columns with high density and long common prefixes
            return (-stats['density'], -stats['prefix_matches'], -stats['avg_length'])
        
        high_density.sort(key=sort_key)
        medium_density.sort(key=sort_key)
        low_density.sort(key=sort_key)
        
        # Combine: high density first, then medium, then low
        return high_density + medium_density + low_density
    
    def _beam_search(
        self,
        df: pd.DataFrame,
        initial_order: List[str],
        col_stats: Dict,
        beam_width: int = 20,
        max_iterations: int = 100
    ) -> Tuple[List[str], float]:
        """Perform beam search for better column ordering."""
        current_beam = [(initial_order, self._evaluate_order(df, initial_order))]
        
        for iteration in range(max_iterations):
            new_candidates = []
            
            for order, score in current_beam:
                # Generate neighbors by swapping adjacent columns
                for i in range(len(order) - 1):
                    new_order = order.copy()
                    new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                    new_score = self._evaluate_order(df, new_order)
                    new_candidates.append((new_order, new_score))
            
            # Combine current beam with new candidates and keep best
            all_candidates = current_beam + new_candidates
            all_candidates.sort(key=lambda x: x[1], reverse=True)
            current_beam = all_candidates[:beam_width]
            
            # Check for convergence
            if iteration > 10 and abs(current_beam[0][1] - current_beam[-1][1]) < 1e-6:
                break
        
        return current_beam[0]
    
    def _evaluate_order(self, df: pd.DataFrame, order: List[str]) -> float:
        """Evaluate a column order by estimating prefix hit rate."""
        n_rows = len(df)
        if n_rows <= 1:
            return 0.0
        
        # Use sampling for efficiency
        sample_size = min(500, n_rows)
        if n_rows > sample_size:
            indices = np.random.choice(n_rows, sample_size, replace=False)
            sample_df = df.iloc[indices][order]
        else:
            sample_df = df[order]
        
        # Convert to concatenated strings
        strings = sample_df.astype(str).apply(lambda row: ''.join(row), axis=1).tolist()
        
        # Calculate approximate hit rate
        total_lcp = 0
        total_length = 0
        
        # Build prefix tree for efficient LCP calculation
        for i in range(len(strings)):
            s = strings[i]
            total_length += len(s)
            
            if i == 0:
                continue
                
            # Find max LCP with previous strings
            max_lcp = 0
            for j in range(i):
                lcp = self._lcp_length(s, strings[j])
                if lcp > max_lcp:
                    max_lcp = lcp
                    # Early exit if we found perfect match
                    if max_lcp == len(s):
                        break
            
            total_lcp += max_lcp
        
        if total_length == 0:
            return 0.0
        
        return total_lcp / total_length
    
    def _lcp_length(self, s1: str, s2: str) -> int:
        """Calculate length of longest common prefix."""
        min_len = min(len(s1), len(s2))
        for i in range(min_len):
            if s1[i] != s2[i]:
                return i
        return min_len
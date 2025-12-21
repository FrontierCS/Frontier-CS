import pandas as pd
import numpy as np
from collections import defaultdict
from itertools import combinations
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
            df = self._apply_merges(df, col_merge)
        
        # Get initial column order
        columns = list(df.columns)
        n_cols = len(columns)
        
        # If few columns, use exhaustive search
        if n_cols <= 10:
            return self._exhaustive_search(df, columns)
        
        # Main optimization algorithm
        optimized_order = self._optimize_column_order(
            df, columns, early_stop, row_stop, col_stop,
            distinct_value_threshold
        )
        
        return df[optimized_order]
    
    def _apply_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Apply column merges by concatenating columns in each group."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if len(merge_group) < 2:
                continue
                
            # Create merged column by concatenating all values in the group
            merged_name = "_".join(merge_group)
            merged_vals = []
            
            for idx in range(len(df)):
                row_vals = [str(result_df.at[idx, col]) for col in merge_group]
                merged_vals.append("".join(row_vals))
            
            result_df[merged_name] = merged_vals
            
            # Remove original columns
            result_df = result_df.drop(columns=merge_group)
        
        return result_df
    
    def _exhaustive_search(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Exhaustive search for small number of columns."""
        from itertools import permutations
        
        best_order = columns
        best_score = self._compute_prefix_hit_rate(df[columns])
        
        # Try all permutations (max 10! = 3.6M)
        for perm in permutations(columns):
            score = self._compute_prefix_hit_rate(df[list(perm)])
            if score > best_score:
                best_score = score
                best_order = list(perm)
        
        return df[best_order]
    
    def _optimize_column_order(
        self, df: pd.DataFrame, columns: list,
        early_stop: int, row_stop: int, col_stop: int,
        distinct_value_threshold: float
    ) -> list:
        """Optimize column order using heuristic approach."""
        n_cols = len(columns)
        n_rows = len(df)
        
        # Compute column statistics
        col_stats = self._compute_column_statistics(df, columns)
        
        # Initialize with greedy ordering based on distinctiveness
        current_order = self._greedy_initial_order(col_stats, distinct_value_threshold)
        current_score = self._compute_prefix_hit_rate(df[current_order])
        
        # Early stopping criteria
        max_iterations = min(early_stop, 1000 * n_cols)
        no_improve_count = 0
        
        # Local search with column swaps
        for iteration in range(max_iterations):
            improved = False
            
            # Try swapping adjacent columns
            for i in range(n_cols - 1):
                new_order = current_order.copy()
                new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                
                score = self._compute_prefix_hit_rate(df[new_order])
                
                if score > current_score:
                    current_order = new_order
                    current_score = score
                    improved = True
                    break
            
            if not improved:
                # Try swapping random pairs
                for _ in range(min(10, n_cols)):
                    i, j = np.random.choice(n_cols, 2, replace=False)
                    new_order = current_order.copy()
                    new_order[i], new_order[j] = new_order[j], new_order[i]
                    
                    score = self._compute_prefix_hit_rate(df[new_order])
                    
                    if score > current_score:
                        current_order = new_order
                        current_score = score
                        improved = True
                        break
            
            if improved:
                no_improve_count = 0
            else:
                no_improve_count += 1
                if no_improve_count >= col_stop * 10:
                    break
        
        return current_order
    
    def _compute_column_statistics(self, df: pd.DataFrame, columns: list) -> dict:
        """Compute statistics for each column."""
        stats = {}
        
        for col in columns:
            # Convert to string and compute lengths
            str_series = df[col].astype(str)
            lengths = str_series.str.len()
            
            # Count distinct values
            distinct_count = str_series.nunique()
            total_count = len(str_series)
            
            # Compute prefix patterns
            prefix_samples = str_series.head(1000).tolist()
            avg_prefix_len = self._average_common_prefix_length(prefix_samples)
            
            stats[col] = {
                'avg_length': lengths.mean(),
                'distinct_ratio': distinct_count / total_count,
                'avg_prefix_len': avg_prefix_len,
                'total_chars': lengths.sum()
            }
        
        return stats
    
    def _average_common_prefix_length(self, samples: list) -> float:
        """Compute average common prefix length among sample strings."""
        if len(samples) < 2:
            return 0.0
        
        total_lcp = 0
        count = 0
        
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                str1 = str(samples[i])
                str2 = str(samples[j])
                
                # Find common prefix length
                lcp_len = 0
                min_len = min(len(str1), len(str2))
                
                for k in range(min_len):
                    if str1[k] == str2[k]:
                        lcp_len += 1
                    else:
                        break
                
                total_lcp += lcp_len
                count += 1
        
        return total_lcp / count if count > 0 else 0.0
    
    def _greedy_initial_order(self, col_stats: dict, threshold: float) -> list:
        """Create initial ordering using greedy heuristic."""
        # Sort columns by distinctiveness and prefix potential
        columns = list(col_stats.keys())
        
        # Compute scores for ordering
        def score_func(col):
            stats = col_stats[col]
            # Prefer columns with low distinct ratio and high prefix potential
            distinct_penalty = stats['distinct_ratio']
            prefix_bonus = stats['avg_prefix_len'] / max(stats['avg_length'], 1)
            return prefix_bonus - distinct_penalty
        
        sorted_cols = sorted(columns, key=score_func, reverse=True)
        
        # Try to place high-distinct columns at the end
        final_order = []
        low_distinct = []
        high_distinct = []
        
        for col in sorted_cols:
            if col_stats[col]['distinct_ratio'] < threshold:
                low_distinct.append(col)
            else:
                high_distinct.append(col)
        
        # Combine: low distinct first, then high distinct
        final_order = low_distinct + high_distinct
        
        return final_order
    
    def _compute_prefix_hit_rate(self, df: pd.DataFrame) -> float:
        """Compute the prefix hit rate for the given column order."""
        n_rows = len(df)
        
        if n_rows < 2:
            return 0.0
        
        # Convert all rows to concatenated strings
        row_strings = []
        for idx in range(n_rows):
            row_str = "".join(str(val) for val in df.iloc[idx].values)
            row_strings.append(row_str)
        
        # Compute prefix hit rate
        total_lcp = 0
        total_length = 0
        
        # Use efficient LCP computation with early stopping
        for i in range(n_rows):
            if i == 0:
                total_length += len(row_strings[i])
                continue
            
            max_lcp = 0
            current_str = row_strings[i]
            current_len = len(current_str)
            total_length += current_len
            
            # Check against previous rows
            for j in range(i):
                prev_str = row_strings[j]
                min_len = min(current_len, len(prev_str))
                
                # Fast LCP computation
                lcp_len = 0
                while lcp_len < min_len and current_str[lcp_len] == prev_str[lcp_len]:
                    lcp_len += 1
                
                if lcp_len > max_lcp:
                    max_lcp = lcp_len
                    # Early stop if we found perfect match
                    if max_lcp == current_len:
                        break
            
            total_lcp += max_lcp
        
        # Return hit rate
        return total_lcp / total_length if total_length > 0 else 0.0

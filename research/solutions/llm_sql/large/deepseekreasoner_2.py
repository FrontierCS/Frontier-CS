import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional
import random
import time
from collections import defaultdict, Counter
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
        
        # Apply column merges if specified
        if col_merge is not None:
            df = self._apply_column_merges(df, col_merge)
        
        # Get column names after merging
        columns = list(df.columns)
        
        # If we have too many columns, use heuristic approach
        if len(columns) > 15:
            # Use greedy heuristic for large column sets
            order = self._greedy_column_order(df, columns)
        else:
            # For smaller column sets, try more exhaustive search
            order = self._optimize_column_order(df, columns, early_stop)
        
        # Reorder columns
        return df[order]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Apply column merges as specified in col_merge."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if len(merge_group) < 2:
                continue
                
            # Create merged column name
            merged_name = "_".join(merge_group)
            
            # Merge columns by concatenating string values
            result_df[merged_name] = result_df[merge_group].apply(
                lambda row: "".join(str(x) for x in row), axis=1
            )
            
            # Remove original columns
            result_df = result_df.drop(columns=merge_group)
        
        return result_df
    
    def _compute_hit_rate(self, df: pd.DataFrame, order: List[str]) -> float:
        """Compute hit rate for a given column order."""
        n_rows = len(df)
        if n_rows < 2:
            return 0.0
        
        # Build strings for each row in the given order
        strings = []
        for _, row in df.iterrows():
            s = "".join(str(row[col]) for col in order)
            strings.append(s)
        
        total_lcp = 0
        total_len = 0
        
        # Use a trie to efficiently compute LCPs
        root = {}
        for i, s in enumerate(strings):
            total_len += len(s)
            
            if i == 0:
                # Build trie for first string
                node = root
                for char in s:
                    if char not in node:
                        node[char] = {}
                    node = node[char]
                continue
            
            # Find LCP with previous strings using trie
            node = root
            lcp = 0
            for char in s:
                if char in node:
                    node = node[char]
                    lcp += 1
                else:
                    break
            
            total_lcp += lcp
            
            # Add current string to trie
            node = root
            for char in s:
                if char not in node:
                    node[char] = {}
                node = node[char]
        
        return total_lcp / total_len if total_len > 0 else 0.0
    
    def _greedy_column_order(self, df: pd.DataFrame, columns: List[str]) -> List[str]:
        """Greedy algorithm to find good column order."""
        # Compute column characteristics
        col_stats = []
        for col in columns:
            values = df[col].astype(str).values
            
            # Compute value lengths
            lengths = [len(v) for v in values]
            avg_len = np.mean(lengths)
            
            # Compute distinctness
            unique_values = len(set(values))
            distinct_ratio = unique_values / len(values)
            
            # Compute prefix similarity within column
            if len(values) > 1:
                sample_size = min(100, len(values))
                sample = random.sample(list(values), sample_size)
                
                # Average LCP between pairs
                lcp_sum = 0
                count = 0
                for i in range(sample_size):
                    for j in range(i+1, sample_size):
                        s1, s2 = sample[i], sample[j]
                        lcp = 0
                        for c1, c2 in zip(s1, s2):
                            if c1 == c2:
                                lcp += 1
                            else:
                                break
                        lcp_sum += lcp
                        count += 1
                avg_column_lcp = lcp_sum / count if count > 0 else 0
            else:
                avg_column_lcp = 0
            
            col_stats.append({
                'col': col,
                'avg_len': avg_len,
                'distinct_ratio': distinct_ratio,
                'avg_lcp': avg_column_lcp,
            })
        
        # Sort columns: high avg_len and low distinct_ratio first
        # This prioritizes columns that provide more characters but are similar across rows
        col_stats.sort(key=lambda x: (x['avg_len'], -x['distinct_ratio']), reverse=True)
        
        # Start with the best column
        order = [col_stats[0]['col']]
        remaining = [s['col'] for s in col_stats[1:]]
        
        # Greedily add columns
        while remaining:
            best_col = None
            best_score = -1
            
            # Try each remaining column
            for i, col in enumerate(remaining[:20]):  # Limit to 20 for speed
                test_order = order + [col]
                score = self._estimate_order_score(df, test_order)
                
                if score > best_score:
                    best_score = score
                    best_col = col
            
            if best_col:
                order.append(best_col)
                remaining.remove(best_col)
            else:
                # Add remaining columns in original order
                order.extend(remaining)
                break
        
        return order
    
    def _estimate_order_score(self, df: pd.DataFrame, order: List[str]) -> float:
        """Estimate score for a partial order without full computation."""
        # Use a small sample of rows for estimation
        sample_size = min(100, len(df))
        if sample_size < 2:
            return 0.0
        
        indices = random.sample(range(len(df)), sample_size)
        sample_df = df.iloc[indices].reset_index(drop=True)
        
        # Compute partial hit rate
        return self._compute_hit_rate(sample_df, order)
    
    def _optimize_column_order(self, df: pd.DataFrame, columns: List[str], early_stop: int) -> List[str]:
        """Optimize column order for smaller column sets."""
        n_cols = len(columns)
        
        # If few columns, try all permutations
        if n_cols <= 6:
            return self._try_all_permutations(df, columns)
        
        # Use beam search
        return self._beam_search(df, columns, early_stop)
    
    def _try_all_permutations(self, df: pd.DataFrame, columns: List[str]) -> List[str]:
        """Try all permutations for small column sets."""
        best_order = None
        best_score = -1
        
        # Use a sample for evaluation
        sample_size = min(500, len(df))
        if sample_size < 2:
            return columns
        
        indices = random.sample(range(len(df)), sample_size)
        sample_df = df.iloc[indices].reset_index(drop=True)
        
        for perm in itertools.permutations(columns):
            score = self._compute_hit_rate(sample_df, list(perm))
            if score > best_score:
                best_score = score
                best_order = list(perm)
        
        return best_order if best_order else columns
    
    def _beam_search(self, df: pd.DataFrame, columns: List[str], beam_width: int) -> List[str]:
        """Beam search for column ordering."""
        # Use a sample for evaluation
        sample_size = min(1000, len(df))
        if sample_size < 2:
            return columns
        
        indices = random.sample(range(len(df)), sample_size)
        sample_df = df.iloc[indices].reset_index(drop=True)
        
        # Start with empty order
        beam = [([], 0.0)]
        
        for _ in range(len(columns)):
            new_beam = []
            
            for order, score in beam:
                remaining = [c for c in columns if c not in order]
                
                # Try adding each remaining column
                for col in remaining[:beam_width*2]:  # Limit candidates for speed
                    new_order = order + [col]
                    new_score = self._compute_hit_rate(sample_df, new_order)
                    new_beam.append((new_order, new_score))
            
            # Keep top beam_width candidates
            new_beam.sort(key=lambda x: x[1], reverse=True)
            beam = new_beam[:beam_width]
        
        # Return best full order
        best_order, best_score = max(beam, key=lambda x: x[1])
        return best_order
    
    def _compute_column_similarity(self, df: pd.DataFrame) -> np.ndarray:
        """Compute similarity matrix between columns."""
        n_cols = len(df.columns)
        sim_matrix = np.zeros((n_cols, n_cols))
        
        # Convert to string arrays
        str_arrays = []
        for col in df.columns:
            str_arrays.append(df[col].astype(str).values)
        
        # Compute pairwise similarities
        for i in range(n_cols):
            for j in range(i, n_cols):
                if i == j:
                    sim_matrix[i, j] = 1.0
                    continue
                
                # Sample pairs for efficiency
                sample_size = min(100, len(df))
                indices = random.sample(range(len(df)), sample_size)
                
                # Compute similarity
                sim_sum = 0
                for idx in indices:
                    s1 = str_arrays[i][idx]
                    s2 = str_arrays[j][idx]
                    
                    # String similarity (Jaccard of character sets)
                    set1 = set(s1)
                    set2 = set(s2)
                    if len(set1 | set2) > 0:
                        sim = len(set1 & set2) / len(set1 | set2)
                    else:
                        sim = 1.0
                    sim_sum += sim
                
                sim_matrix[i, j] = sim_matrix[j, i] = sim_sum / sample_size
        
        return sim_matrix
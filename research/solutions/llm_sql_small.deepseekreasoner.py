import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
from collections import defaultdict
import time
import math
from multiprocessing import Pool, cpu_count
import itertools

class TrieNode:
    __slots__ = ('children', 'count')
    def __init__(self):
        self.children = {}
        self.count = 0

class Trie:
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
            node.count += 1
    
    def total_common_prefix_length(self) -> int:
        total = 0
        stack = [self.root]
        while stack:
            node = stack.pop()
            for child in node.children.values():
                if child.count > 1:
                    total += child.count * (child.count - 1) // 2
                stack.append(child)
        return total

class Solution:
    def __init__(self):
        self.cached_strings = {}
    
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
        
        # Step 1: Apply column merges
        if col_merge is not None:
            df = df.copy()
            for group in col_merge:
                if len(group) > 1:
                    # Merge columns in the group
                    merged_col = df[group[0]].astype(str)
                    for col in group[1:]:
                        merged_col += df[col].astype(str)
                    df[group[0]] = merged_col
                    df = df.drop(columns=group[1:])
        
        # If only one column, return as is
        if len(df.columns) <= 1:
            return df
        
        # Step 2: Preprocess data
        columns = list(df.columns)
        M = len(columns)
        
        # Convert all values to strings and cache
        str_data = {}
        for col in columns:
            str_data[col] = df[col].astype(str).values
        
        # Step 3: Compute column scores based on common prefix length
        scores = {}
        N = len(df)
        for col in columns:
            trie = Trie()
            for val in str_data[col]:
                trie.insert(val)
            total_lcp = trie.total_common_prefix_length()
            if N > 1:
                score = total_lcp / (N * (N - 1) / 2)
            else:
                score = 0
            scores[col] = score
        
        # Step 4: Initial permutation - sort by score descending
        sorted_cols = sorted(columns, key=lambda x: scores[x], reverse=True)
        
        # Step 5: Evaluate initial permutation
        best_perm = sorted_cols
        best_score = self._evaluate_permutation(str_data, best_perm, df)
        
        # Step 6: Local search with adjacent swaps
        if M > 1 and early_stop > 0:
            current_perm = best_perm.copy()
            current_score = best_score
            
            # Create subset for faster evaluation
            subset_size = min(row_stop * 1000, N)  # Use row_stop as multiplier
            if subset_size < N:
                indices = np.random.choice(N, size=subset_size, replace=False)
                subset_data = {}
                for col in columns:
                    subset_data[col] = str_data[col][indices]
            else:
                subset_data = str_data
            
            iterations = 0
            improved = True
            
            while improved and iterations < early_stop:
                improved = False
                
                # Generate all adjacent swaps
                swaps = []
                for i in range(M-1):
                    new_perm = current_perm.copy()
                    new_perm[i], new_perm[i+1] = new_perm[i+1], new_perm[i]
                    swaps.append(new_perm)
                
                # Evaluate swaps
                swap_scores = []
                if parallel and len(swaps) > 1:
                    with Pool(min(cpu_count(), len(swaps))) as pool:
                        args = [(subset_data, perm) for perm in swaps]
                        swap_scores = pool.starmap(self._evaluate_permutation_subset, args)
                else:
                    for perm in swaps:
                        score = self._evaluate_permutation_subset(subset_data, perm)
                        swap_scores.append(score)
                
                # Find best swap
                best_idx = np.argmax(swap_scores)
                best_swap_score = swap_scores[best_idx]
                
                if best_swap_score > current_score + 1e-12:
                    current_perm = swaps[best_idx]
                    current_score = best_swap_score
                    improved = True
                    iterations += M - 1
                    
                    # Evaluate on full dataset
                    full_score = self._evaluate_permutation(str_data, current_perm, df)
                    if full_score > best_score + 1e-12:
                        best_perm = current_perm.copy()
                        best_score = full_score
                else:
                    break
            
            # Additional optimization: try random permutations if time permits
            remaining_iterations = early_stop - iterations
            if remaining_iterations > 0 and M > 2:
                num_random = min(remaining_iterations, 1000)
                for _ in range(num_random):
                    perm = np.random.permutation(columns).tolist()
                    score = self._evaluate_permutation_subset(subset_data, perm)
                    if score > current_score + 1e-12:
                        current_perm = perm
                        current_score = score
                        # Evaluate on full dataset
                        full_score = self._evaluate_permutation(str_data, current_perm, df)
                        if full_score > best_score + 1e-12:
                            best_perm = current_perm.copy()
                            best_score = full_score
        
        # Ensure we don't exceed time limit
        if time.time() - start_time > 9.5:  # Leave some margin
            print("Warning: approaching time limit")
        
        # Return reordered DataFrame
        return df[best_perm]
    
    def _evaluate_permutation(self, str_data: Dict[str, np.ndarray], 
                             perm: List[str], df: pd.DataFrame) -> float:
        """Evaluate permutation on full dataset."""
        N = len(next(iter(str_data.values())))
        if N == 0:
            return 0.0
        
        # Build concatenated strings
        strings = []
        for i in range(N):
            parts = []
            for col in perm:
                parts.append(str_data[col][i])
            strings.append(''.join(parts))
        
        # Compute hit rate using trie
        total_lcp = 0
        total_len = 0
        trie = Trie()
        
        for s in strings:
            # Find LCP with existing strings
            node = trie.root
            lcp = 0
            for ch in s:
                if ch in node.children:
                    node = node.children[ch]
                    lcp += 1
                else:
                    break
            total_lcp += lcp
            total_len += len(s)
            # Insert into trie
            trie.insert(s)
        
        if total_len == 0:
            return 0.0
        return total_lcp / total_len
    
    def _evaluate_permutation_subset(self, str_data: Dict[str, np.ndarray],
                                    perm: List[str]) -> float:
        """Evaluate permutation on subset data (faster)."""
        N = len(next(iter(str_data.values())))
        if N == 0:
            return 0.0
        
        # Build concatenated strings
        strings = []
        for i in range(N):
            parts = []
            for col in perm:
                parts.append(str_data[col][i])
            strings.append(''.join(parts))
        
        # Compute hit rate using trie
        total_lcp = 0
        total_len = 0
        trie = Trie()
        
        for s in strings:
            node = trie.root
            lcp = 0
            for ch in s:
                if ch in node.children:
                    node = node.children[ch]
                    lcp += 1
                else:
                    break
            total_lcp += lcp
            total_len += len(s)
            trie.insert(s)
        
        if total_len == 0:
            return 0.0
        return total_lcp / total_len

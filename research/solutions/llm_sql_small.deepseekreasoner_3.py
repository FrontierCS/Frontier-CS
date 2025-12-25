import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Set, Optional
import itertools
from collections import defaultdict
import multiprocessing as mp
from functools import partial
import time

class TrieNode:
    def __init__(self):
        self.children = {}
        self.count = 0

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
        
        # Apply column merges first
        if col_merge is not None:
            df = self._apply_column_merges(df, col_merge)
        
        # If only one column, return as is
        if len(df.columns) <= 1:
            return df
        
        # Get original column order
        original_cols = list(df.columns)
        n_cols = len(original_cols)
        
        # Sample rows for faster evaluation if dataset is large
        if len(df) > row_stop:
            sample_df = df.sample(n=min(row_stop, len(df)), random_state=42)
        else:
            sample_df = df
        
        # Analyze column characteristics
        col_stats = self._analyze_columns(sample_df, distinct_value_threshold)
        
        # Generate candidate permutations using heuristic approach
        candidate_perms = self._generate_candidate_permutations(
            original_cols, col_stats, n_cols, early_stop
        )
        
        # Evaluate permutations
        if parallel and len(candidate_perms) > 1:
            best_perm = self._evaluate_permutations_parallel(
                df, candidate_perms, start_time
            )
        else:
            best_perm = self._evaluate_permutations_sequential(
                df, candidate_perms, start_time
            )
        
        # Reorder columns
        return df[best_perm]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Merge columns according to specifications."""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if not merge_group:
                continue
                
            # Create merged column
            merged_col_name = '_'.join(merge_group)
            merged_values = []
            
            for idx in range(len(df)):
                row_values = []
                for col in merge_group:
                    if col in df.columns:
                        row_values.append(str(df.iloc[idx][col]))
                merged_values.append(''.join(row_values))
            
            result_df[merged_col_name] = merged_values
            
            # Remove original columns
            for col in merge_group:
                if col in result_df.columns:
                    result_df = result_df.drop(columns=[col])
        
        return result_df
    
    def _analyze_columns(self, df: pd.DataFrame, threshold: float) -> Dict:
        """Analyze column statistics for heuristic ordering."""
        stats = {}
        
        for col in df.columns:
            col_data = df[col].astype(str)
            n_unique = col_data.nunique()
            n_total = len(col_data)
            
            # Calculate distinctiveness ratio
            distinct_ratio = n_unique / n_total if n_total > 0 else 0
            
            # Calculate average string length
            avg_len = col_data.str.len().mean()
            
            # Calculate prefix distribution (first character)
            first_chars = col_data.str[0] if col_data.str.len().min() > 0 else pd.Series([''])
            first_char_dist = first_chars.value_counts(normalize=True)
            max_first_char_ratio = first_char_dist.max() if len(first_char_dist) > 0 else 0
            
            stats[col] = {
                'distinct_ratio': distinct_ratio,
                'avg_len': avg_len,
                'max_first_char_ratio': max_first_char_ratio,
                'n_unique': n_unique,
                'is_low_distinct': distinct_ratio <= threshold,
                'is_high_distinct': distinct_ratio > threshold,
            }
        
        return stats
    
    def _generate_candidate_permutations(
        self, 
        cols: List[str], 
        col_stats: Dict, 
        n_cols: int, 
        early_stop: int
    ) -> List[List[str]]:
        """Generate candidate permutations using heuristics."""
        candidates = []
        
        # Strategy 1: Sort by distinctiveness (lowest first for early columns)
        sorted_low_distinct = sorted(
            [c for c in cols if col_stats[c]['is_low_distinct']],
            key=lambda x: col_stats[x]['distinct_ratio']
        )
        sorted_high_distinct = sorted(
            [c for c in cols if not col_stats[c]['is_low_distinct']],
            key=lambda x: -col_stats[x]['distinct_ratio']
        )
        perm1 = sorted_low_distinct + sorted_high_distinct
        if len(perm1) == n_cols:
            candidates.append(perm1)
        
        # Strategy 2: Sort by average length (shortest first)
        perm2 = sorted(cols, key=lambda x: col_stats[x]['avg_len'])
        if perm2 not in candidates:
            candidates.append(perm2)
        
        # Strategy 3: Sort by first character dominance (highest first)
        perm3 = sorted(cols, key=lambda x: -col_stats[x]['max_first_char_ratio'])
        if perm3 not in candidates:
            candidates.append(perm3)
        
        # Strategy 4: Original order
        perm4 = cols
        if perm4 not in candidates:
            candidates.append(perm4)
        
        # Generate additional permutations by swapping adjacent columns
        base_perm = candidates[0]
        swap_candidates = [base_perm]
        
        for i in range(len(base_perm) - 1):
            new_perm = base_perm.copy()
            new_perm[i], new_perm[i + 1] = new_perm[i + 1], new_perm[i]
            swap_candidates.append(new_perm)
            
            # Also try swapping with offset of 2
            if i + 2 < len(base_perm):
                new_perm2 = base_perm.copy()
                new_perm2[i], new_perm2[i + 2] = new_perm2[i + 2], new_perm2[i]
                swap_candidates.append(new_perm2)
        
        # Add unique permutations from swap candidates
        for perm in swap_candidates:
            if perm not in candidates:
                candidates.append(perm)
        
        # If we have few candidates, generate more random permutations
        if len(candidates) < min(early_stop // 100, 10) and n_cols <= 8:
            # Generate additional permutations systematically
            n_needed = min(early_stop // 100, 20) - len(candidates)
            if n_needed > 0:
                additional = self._generate_systematic_permutations(cols, n_needed)
                for perm in additional:
                    if perm not in candidates:
                        candidates.append(perm)
        
        return candidates[:early_stop]
    
    def _generate_systematic_permutations(
        self, 
        cols: List[str], 
        n_perms: int
    ) -> List[List[str]]:
        """Generate systematic permutations for small column sets."""
        if len(cols) <= 6:
            # Generate all permutations for small sets
            all_perms = list(itertools.permutations(cols))
            selected = []
            step = max(1, len(all_perms) // n_perms)
            for i in range(0, min(len(all_perms), n_perms * step), step):
                selected.append(list(all_perms[i]))
            return selected
        else:
            # Use greedy insertion for larger sets
            perms = []
            base = list(cols)
            
            for _ in range(n_perms):
                # Random shuffle as base
                np.random.shuffle(base)
                
                # Create variations by moving one element
                for i in range(len(base)):
                    for j in range(i + 1, min(i + 4, len(base))):
                        new_perm = base.copy()
                        new_perm[i], new_perm[j] = new_perm[j], new_perm[i]
                        if new_perm not in perms:
                            perms.append(new_perm)
                            if len(perms) >= n_perms:
                                return perms
            
            return perms
    
    def _evaluate_permutations_sequential(
        self, 
        df: pd.DataFrame, 
        permutations: List[List[str]], 
        start_time: float
    ) -> List[str]:
        """Evaluate permutations sequentially and return the best one."""
        best_score = -1
        best_perm = permutations[0]
        
        for perm in permutations:
            # Check time limit
            if time.time() - start_time > 9.5:
                break
                
            score = self._evaluate_permutation(df, perm)
            if score > best_score:
                best_score = score
                best_perm = perm
        
        return best_perm
    
    def _evaluate_permutations_parallel(
        self, 
        df: pd.DataFrame, 
        permutations: List[List[str]], 
        start_time: float
    ) -> List[str]:
        """Evaluate permutations in parallel and return the best one."""
        # Use a subset for parallel evaluation to avoid overhead
        n_workers = min(mp.cpu_count(), 4)  # Limit to 4 workers for CPU-only environment
        n_perms = len(permutations)
        
        # Split permutations into chunks
        chunk_size = max(1, n_perms // n_workers)
        chunks = []
        for i in range(0, n_perms, chunk_size):
            chunks.append(permutations[i:i + chunk_size])
        
        # Evaluate in parallel
        with mp.Pool(processes=n_workers) as pool:
            results = pool.map(
                partial(self._evaluate_permutations_chunk, df, start_time),
                chunks
            )
        
        # Find best overall
        best_score = -1
        best_perm = permutations[0]
        
        for chunk_best_perm, chunk_best_score in results:
            if chunk_best_score > best_score:
                best_score = chunk_best_score
                best_perm = chunk_best_perm
        
        return best_perm
    
    def _evaluate_permutations_chunk(
        self, 
        df: pd.DataFrame, 
        start_time: float, 
        permutations: List[List[str]]
    ) -> Tuple[List[str], float]:
        """Evaluate a chunk of permutations."""
        best_score = -1
        best_perm = permutations[0]
        
        for perm in permutations:
            # Check time limit
            if time.time() - start_time > 9.5:
                break
                
            score = self._evaluate_permutation(df, perm)
            if score > best_score:
                best_score = score
                best_perm = perm
        
        return best_perm, best_score
    
    def _evaluate_permutation(
        self, 
        df: pd.DataFrame, 
        permutation: List[str]
    ) -> float:
        """Evaluate a single permutation by calculating hit rate."""
        # Convert to string rows
        rows = []
        for idx in range(len(df)):
            row_vals = []
            for col in permutation:
                row_vals.append(str(df.iloc[idx][col]))
            rows.append(''.join(row_vals))
        
        # Calculate hit rate using prefix tree for efficiency
        return self._calculate_hit_rate_trie(rows)
    
    def _calculate_hit_rate_trie(self, rows: List[str]) -> float:
        """Calculate hit rate using a prefix tree for O(L) per row."""
        root = TrieNode()
        total_lcp = 0
        total_len = 0
        
        for i, row_str in enumerate(rows):
            total_len += len(row_str)
            
            if i == 0:
                # Insert first row
                node = root
                for char in row_str:
                    if char not in node.children:
                        node.children[char] = TrieNode()
                    node = node.children[char]
                    node.count += 1
                continue
            
            # Find LCP with previous rows
            node = root
            lcp = 0
            for char in row_str:
                if char in node.children:
                    node = node.children[char]
                    lcp += 1
                else:
                    break
            
            total_lcp += lcp
            
            # Insert current row
            node = root
            for char in row_str:
                if char not in node.children:
                    node.children[char] = TrieNode()
                node = node.children[char]
                node.count += 1
        
        # Avoid division by zero
        if total_len == 0:
            return 0.0
        
        return total_lcp / total_len

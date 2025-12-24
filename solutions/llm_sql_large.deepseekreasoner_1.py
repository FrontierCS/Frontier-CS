import pandas as pd
import numpy as np
from collections import defaultdict
from typing import List, Tuple, Dict, Set
import itertools
from dataclasses import dataclass
import time

@dataclass
class TrieNode:
    children: Dict[str, 'TrieNode']
    count: int
    row_indices: List[int]

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
            df = self.apply_column_merges(df, col_merge)
        
        # Get column order that maximizes prefix hit rate
        column_order = self.optimize_column_order(df)
        
        # Return dataframe with reordered columns
        return df[column_order]
    
    def apply_column_merges(self, df: pd.DataFrame, col_merge: List[List[str]]) -> pd.DataFrame:
        """Apply column merges by concatenating specified columns."""
        new_df = df.copy()
        
        for merge_group in col_merge:
            # Ensure all columns in the group exist
            valid_cols = [col for col in merge_group if col in new_df.columns]
            if not valid_cols:
                continue
            
            # Create merged column
            merged_name = '_'.join(valid_cols)
            new_df[merged_name] = new_df[valid_cols].astype(str).agg(''.join, axis=1)
            
            # Remove original columns
            new_df = new_df.drop(columns=valid_cols)
        
        return new_df
    
    def optimize_column_order(self, df: pd.DataFrame) -> List[str]:
        """Find column order that maximizes prefix hit rate."""
        n_rows, n_cols = df.shape
        
        # Convert to string and compute string representations
        str_df = df.astype(str)
        
        # Precompute column information
        col_info = []
        for col in str_df.columns:
            values = str_df[col].values
            # Distinct value ratio
            distinct_ratio = len(np.unique(values)) / n_rows
            # Average string length
            avg_len = np.mean([len(x) for x in values])
            col_info.append((col, distinct_ratio, avg_len))
        
        # Sort columns by distinct ratio (lowest first) then average length (shortest first)
        sorted_cols = sorted(col_info, key=lambda x: (x[1], x[2]))
        base_order = [col for col, _, _ in sorted_cols]
        
        # Try multiple strategies and pick the best
        strategies = [
            self.greedy_optimization,
            self.trie_based_optimization,
            self.heuristic_optimization
        ]
        
        best_order = base_order
        best_score = self.evaluate_order(str_df, base_order)
        
        for strategy in strategies:
            try:
                candidate_order = strategy(str_df, base_order)
                score = self.evaluate_order(str_df, candidate_order)
                if score > best_score:
                    best_score = score
                    best_order = candidate_order
            except:
                continue
        
        # Local search improvement
        improved_order = self.local_search(str_df, best_order)
        if self.evaluate_order(str_df, improved_order) > best_score:
            best_order = improved_order
        
        return best_order
    
    def greedy_optimization(self, str_df: pd.DataFrame, initial_order: List[str]) -> List[str]:
        """Greedy algorithm to build column order."""
        remaining = set(initial_order)
        ordered = []
        
        while remaining:
            best_col = None
            best_gain = -1
            
            for col in remaining:
                candidate_order = ordered + [col]
                gain = self.evaluate_order(str_df, candidate_order)
                
                if gain > best_gain:
                    best_gain = gain
                    best_col = col
            
            if best_col:
                ordered.append(best_col)
                remaining.remove(best_col)
            else:
                # Fallback: add remaining columns in original order
                ordered.extend(sorted(remaining))
                break
        
        return ordered
    
    def trie_based_optimization(self, str_df: pd.DataFrame, initial_order: List[str]) -> List[str]:
        """Optimize using trie-based analysis of column prefixes."""
        n_rows, n_cols = str_df.shape
        
        # Build frequency matrix for column values
        col_freq = {}
        for col in str_df.columns:
            value_counts = str_df[col].value_counts()
            col_freq[col] = {
                'entropy': self.calculate_entropy(value_counts),
                'common_values': set(value_counts.nlargest(3).index)
            }
        
        # Sort by entropy (lowest first)
        sorted_cols = sorted(col_freq.items(), key=lambda x: x[1]['entropy'])
        
        # Group columns with similar common values
        ordered = []
        used = set()
        
        # Start with lowest entropy column
        if sorted_cols:
            first_col = sorted_cols[0][0]
            ordered.append(first_col)
            used.add(first_col)
        
        # Greedily add columns that share common values with current prefix
        while len(ordered) < len(str_df.columns):
            best_col = None
            best_overlap = -1
            
            for col, info in sorted_cols:
                if col in used:
                    continue
                
                # Estimate overlap with current columns
                overlap_score = self.estimate_column_overlap(str_df, ordered, col)
                
                if overlap_score > best_overlap:
                    best_overlap = overlap_score
                    best_col = col
            
            if best_col:
                ordered.append(best_col)
                used.add(best_col)
            else:
                # Add remaining columns
                for col, _ in sorted_cols:
                    if col not in used:
                        ordered.append(col)
                break
        
        return ordered
    
    def heuristic_optimization(self, str_df: pd.DataFrame, initial_order: List[str]) -> List[str]:
        """Heuristic optimization based on column statistics."""
        n_rows = len(str_df)
        
        # Calculate column statistics
        stats = []
        for col in str_df.columns:
            values = str_df[col].values
            # Distinctness
            distinct_count = len(np.unique(values))
            distinct_ratio = distinct_count / n_rows
            
            # String length statistics
            lengths = [len(x) for x in values]
            avg_len = np.mean(lengths)
            len_variance = np.var(lengths)
            
            # Common prefix within column
            if distinct_count < n_rows:
                # Find most common value
                value_counts = pd.Series(values).value_counts()
                most_common = value_counts.index[0]
                common_ratio = value_counts.iloc[0] / n_rows
            else:
                common_ratio = 0
            
            # Combined score (lower is better for early placement)
            # We want columns with low distinct ratio, low avg length, and high common ratio
            score = (distinct_ratio * 0.5 + avg_len / 100 * 0.3 - common_ratio * 0.2)
            stats.append((col, score, distinct_ratio, avg_len, common_ratio))
        
        # Sort by combined score
        stats.sort(key=lambda x: x[1])
        return [col for col, _, _, _, _ in stats]
    
    def local_search(self, str_df: pd.DataFrame, initial_order: List[str]) -> List[str]:
        """Improve order through local search."""
        current_order = initial_order.copy()
        current_score = self.evaluate_order(str_df, current_order)
        
        improved = True
        max_iterations = min(50, len(current_order))
        
        for _ in range(max_iterations):
            if not improved:
                break
            
            improved = False
            
            # Try swapping adjacent pairs
            for i in range(len(current_order) - 1):
                new_order = current_order.copy()
                new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                
                new_score = self.evaluate_order(str_df, new_order)
                
                if new_score > current_score:
                    current_order = new_order
                    current_score = new_score
                    improved = True
                    break
            
            # Try moving a column to different position
            if not improved and len(current_order) > 3:
                for i in range(len(current_order)):
                    for j in range(len(current_order)):
                        if i == j:
                            continue
                        
                        new_order = current_order.copy()
                        col = new_order.pop(i)
                        new_order.insert(j, col)
                        
                        new_score = self.evaluate_order(str_df, new_order)
                        
                        if new_score > current_score:
                            current_order = new_order
                            current_score = new_score
                            improved = True
                            break
                    
                    if improved:
                        break
        
        return current_order
    
    def evaluate_order(self, str_df: pd.DataFrame, column_order: List[str]) -> float:
        """Evaluate the prefix hit rate for a given column order."""
        n_rows = len(str_df)
        
        if n_rows <= 1:
            return 0.0
        
        # Take subset if too many rows for performance
        max_rows = 1000
        if n_rows > max_rows:
            # Sample rows for evaluation
            indices = np.linspace(0, n_rows - 1, max_rows, dtype=int)
            sample_df = str_df.iloc[indices][column_order]
        else:
            sample_df = str_df[column_order]
        
        n_rows = len(sample_df)
        
        # Build concatenated strings
        strings = []
        total_len = 0
        
        for _, row in sample_df.iterrows():
            s = ''.join(row.values)
            strings.append(s)
            total_len += len(s)
        
        if total_len == 0:
            return 0.0
        
        # Calculate prefix hit rate
        lcp_sum = 0
        
        # Use a trie for efficient LCP computation
        root = TrieNode(children={}, count=0, row_indices=[])
        
        for i, s in enumerate(strings):
            if i == 0:
                # Insert first string
                node = root
                for ch in s:
                    if ch not in node.children:
                        node.children[ch] = TrieNode(children={}, count=0, row_indices=[])
                    node = node.children[ch]
                    node.count += 1
                    node.row_indices.append(i)
                continue
            
            # Find LCP with existing strings
            node = root
            lcp = 0
            for ch in s:
                if ch in node.children:
                    node = node.children[ch]
                    lcp += 1
                else:
                    break
            
            lcp_sum += lcp
            
            # Insert current string
            node = root
            for ch in s:
                if ch not in node.children:
                    node.children[ch] = TrieNode(children={}, count=0, row_indices=[])
                node = node.children[ch]
                node.count += 1
                node.row_indices.append(i)
        
        return lcp_sum / total_len if total_len > 0 else 0.0
    
    def calculate_entropy(self, value_counts: pd.Series) -> float:
        """Calculate entropy of a column's value distribution."""
        total = value_counts.sum()
        if total == 0:
            return 0.0
        
        probs = value_counts / total
        return -np.sum(probs * np.log2(probs + 1e-10))
    
    def estimate_column_overlap(self, str_df: pd.DataFrame, current_cols: List[str], new_col: str) -> float:
        """Estimate how much a new column overlaps with current prefix."""
        if not current_cols:
            return 0.0
        
        # Sample rows for estimation
        n_samples = min(100, len(str_df))
        indices = np.random.choice(len(str_df), n_samples, replace=False)
        
        sample = str_df.iloc[indices]
        
        # Build prefix strings
        prefix_strings = []
        for _, row in sample[current_cols].iterrows():
            prefix_strings.append(''.join(row.values))
        
        # Get new column values
        new_values = sample[new_col].values
        
        # Calculate overlap
        overlap = 0
        value_to_prefix = {}
        
        for i, (prefix, val) in enumerate(zip(prefix_strings, new_values)):
            key = (prefix, val)
            if key in value_to_prefix:
                # This (prefix, value) pair has been seen before
                overlap += 1
            else:
                value_to_prefix[key] = i
        
        return overlap / n_samples

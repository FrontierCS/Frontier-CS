import pandas as pd
import numpy as np
from collections import defaultdict
import heapq
from itertools import permutations
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
        
        # If 0 or 1 columns, return as is
        if len(df.columns) <= 1:
            return df
        
        # Convert all values to strings
        df_str = df.astype(str)
        
        # Get column data for analysis
        col_data = self._analyze_columns(df_str)
        
        # Try different reordering strategies
        best_order = self._find_best_column_order(df_str, col_data, early_stop)
        
        # Return dataframe with reordered columns
        return df[best_order]
    
    def _apply_column_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        """Merge columns as specified in col_merge"""
        result_df = df.copy()
        
        for merge_group in col_merge:
            if not merge_group:
                continue
                
            # Get the columns to merge
            cols_to_merge = [col for col in merge_group if col in df.columns]
            if len(cols_to_merge) <= 1:
                continue
            
            # Create merged column name
            merged_name = "_".join(cols_to_merge)
            
            # Merge columns (concatenate as strings)
            merged_vals = df[cols_to_merge[0]].astype(str)
            for col in cols_to_merge[1:]:
                merged_vals += df[col].astype(str)
            
            # Add merged column and remove original columns
            result_df[merged_name] = merged_vals
            result_df = result_df.drop(columns=cols_to_merge)
        
        return result_df
    
    def _analyze_columns(self, df: pd.DataFrame) -> dict:
        """Analyze columns for distinct values and patterns"""
        col_data = {}
        
        for col in df.columns:
            values = df[col].values
            unique_vals = np.unique(values)
            col_data[col] = {
                'unique_count': len(unique_vals),
                'unique_ratio': len(unique_vals) / len(values),
                'avg_len': np.mean([len(str(v)) for v in values]),
                'values': values
            }
        
        return col_data
    
    def _calculate_lcp_score(self, df: pd.DataFrame, col_order: list) -> float:
        """Calculate the LCP score for a given column order"""
        n_rows = len(df)
        
        # Build concatenated strings with given column order
        strings = []
        for i in range(n_rows):
            s = ''.join(df.iloc[i][col_order].values)
            strings.append(s)
        
        # Calculate prefix hit rate
        total_lcp = 0
        total_length = 0
        
        # Use incremental LCP calculation
        for i in range(n_rows):
            s_i = strings[i]
            total_length += len(s_i)
            
            if i == 0:
                continue
            
            # Find max LCP with previous strings
            max_lcp = 0
            for j in range(i):
                # Calculate LCP efficiently
                lcp = 0
                min_len = min(len(s_i), len(strings[j]))
                while lcp < min_len and s_i[lcp] == strings[j][lcp]:
                    lcp += 1
                
                if lcp > max_lcp:
                    max_lcp = lcp
                    # Early break if we find perfect match
                    if max_lcp == len(s_i):
                        break
            
            total_lcp += max_lcp
        
        if total_length == 0:
            return 0.0
        
        return total_lcp / total_length
    
    def _find_best_column_order(self, df: pd.DataFrame, col_data: dict, early_stop: int) -> list:
        """Find the best column order using heuristic search"""
        columns = list(df.columns)
        n_cols = len(columns)
        
        # If small number of columns, try all permutations
        if n_cols <= 6:
            best_order = columns
            best_score = self._calculate_lcp_score(df, best_order)
            
            for perm in permutations(columns):
                score = self._calculate_lcp_score(df, list(perm))
                if score > best_score:
                    best_score = score
                    best_order = list(perm)
            
            return best_order
        
        # For larger number of columns, use heuristic approach
        
        # Strategy 1: Sort by unique ratio (fewer unique values first)
        order1 = sorted(columns, 
                       key=lambda c: (col_data[c]['unique_ratio'], 
                                     -col_data[c]['avg_len']))
        
        # Strategy 2: Sort by average length (shorter first)
        order2 = sorted(columns, 
                       key=lambda c: (col_data[c]['avg_len'], 
                                     col_data[c]['unique_ratio']))
        
        # Strategy 3: Use column similarity clustering
        order3 = self._cluster_based_order(df, col_data)
        
        # Try the three strategies and pick the best
        orders = [order1, order2, order3]
        scores = [self._calculate_lcp_score(df, order) for order in orders]
        
        # Also try reverse orders
        for i in range(3):
            rev_order = list(reversed(orders[i]))
            rev_score = self._calculate_lcp_score(df, rev_order)
            orders.append(rev_order)
            scores.append(rev_score)
        
        # Try some random permutations for diversity
        np.random.seed(42)
        for _ in range(min(10, early_stop // 1000)):
            rand_order = np.random.permutation(columns).tolist()
            rand_score = self._calculate_lcp_score(df, rand_order)
            orders.append(rand_order)
            scores.append(rand_score)
        
        # Find best order
        best_idx = np.argmax(scores)
        best_order = orders[best_idx]
        best_score = scores[best_idx]
        
        # Local optimization: try swapping adjacent pairs
        improved = True
        while improved:
            improved = False
            current_order = best_order.copy()
            current_score = best_score
            
            for i in range(n_cols - 1):
                new_order = current_order.copy()
                new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                
                new_score = self._calculate_lcp_score(df, new_order)
                if new_score > current_score:
                    best_order = new_order
                    best_score = new_score
                    improved = True
                    break
        
        # Try moving each column to front
        for i in range(n_cols):
            if i == 0:
                continue
                
            new_order = best_order.copy()
            col = new_order.pop(i)
            new_order.insert(0, col)
            
            new_score = self._calculate_lcp_score(df, new_order)
            if new_score > best_score:
                best_score = new_score
                best_order = new_order
        
        return best_order
    
    def _cluster_based_order(self, df: pd.DataFrame, col_data: dict) -> list:
        """Order columns based on value similarity clustering"""
        columns = list(df.columns)
        n_cols = len(columns)
        
        if n_cols <= 2:
            return columns
        
        # Calculate pairwise column similarity
        similarity = np.zeros((n_cols, n_cols))
        
        # Use value overlap as similarity metric
        for i in range(n_cols):
            for j in range(i + 1, n_cols):
                col_i = columns[i]
                col_j = columns[j]
                
                # For efficiency, sample rows
                n_samples = min(1000, len(df))
                indices = np.random.choice(len(df), n_samples, replace=False)
                
                vals_i = df.iloc[indices][col_i].values
                vals_j = df.iloc[indices][col_j].values
                
                # Calculate exact match ratio
                matches = np.sum(vals_i == vals_j)
                similarity[i, j] = matches / n_samples
                similarity[j, i] = similarity[i, j]
        
        # Build order using greedy approach: start with column that has highest average similarity
        avg_similarity = np.mean(similarity, axis=1)
        start_idx = np.argmax(avg_similarity)
        
        order = [columns[start_idx]]
        used = {start_idx}
        
        while len(order) < n_cols:
            last_idx = columns.index(order[-1])
            best_next = -1
            best_sim = -1
            
            for i in range(n_cols):
                if i not in used:
                    sim = similarity[last_idx, i]
                    if sim > best_sim:
                        best_sim = sim
                        best_next = i
            
            if best_next != -1:
                order.append(columns[best_next])
                used.add(best_next)
        
        return order
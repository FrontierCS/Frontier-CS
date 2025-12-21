import pandas as pd
import random
from collections import Counter

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
        # Apply column merges
        if col_merge is not None:
            df = self._apply_merges(df, col_merge)
        
        # Precompute column strings
        cols = df.columns.tolist()
        M = len(cols)
        if M == 0:
            return df
        
        col_strings = {col: df[col].astype(str).tolist() for col in cols}
        N = len(df)
        
        # Heuristic initial order
        init_order = self._heuristic_order(col_strings, distinct_value_threshold)
        
        best_order = init_order
        if early_stop > 0 and M > 1:
            eval_rows = min(row_stop, N) if row_stop > 0 else N
            subset_indices = list(range(eval_rows))
            best_score = self._evaluate_order(col_strings, init_order, subset_indices)
            current_order, current_score = init_order, best_score
            
            for _ in range(early_stop):
                i, j = random.sample(range(M), 2)
                new_order = current_order.copy()
                new_order[i], new_order[j] = new_order[j], new_order[i]
                new_score = self._evaluate_order(col_strings, new_order, subset_indices)
                if new_score > current_score:
                    current_order, current_score = new_order, new_score
                    if new_score > best_score:
                        best_order, best_score = new_order, new_score
        
        return df[best_order]
    
    def _apply_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        df = df.copy()
        for group in col_merge:
            if not all(col in df.columns for col in group):
                continue
            new_name = "__".join(group)
            df[new_name] = df[group].apply(lambda row: ''.join(row.astype(str)), axis=1)
            df.drop(columns=group, inplace=True)
        return df
    
    def _heuristic_order(self, col_strings: dict, threshold: float) -> list:
        cols = list(col_strings.keys())
        if not cols:
            return cols
        N = len(next(iter(col_strings.values())))
        metrics = []
        for col in cols:
            strings = col_strings[col]
            freq = Counter(strings)
            match_prob = sum((c / N) ** 2 for c in freq.values())
            avg_len = sum(len(s) for s in strings) / N
            metrics.append((col, match_prob, avg_len))
        metrics.sort(key=lambda x: (-x[1], -x[2]))
        return [m[0] for m in metrics]
    
    def _evaluate_order(self, col_strings: dict, order: list, row_indices: list) -> float:
        rows = sorted(row_indices)
        if not rows:
            return 0.0
        col_lists = [col_strings[col] for col in order]
        trie = {}
        total_lcp = 0
        total_len = 0
        for r in rows:
            parts = [col_lists[c][r] for c in range(len(order))]
            s = ''.join(parts)
            total_len += len(s)
            node = trie
            lcp = 0
            for ch in s:
                if ch in node:
                    node = node[ch]
                    lcp += 1
                else:
                    break
            total_lcp += lcp
            node = trie
            for ch in s:
                if ch not in node:
                    node[ch] = {}
                node = node[ch]
        return total_lcp / total_len if total_len > 0 else 0.0

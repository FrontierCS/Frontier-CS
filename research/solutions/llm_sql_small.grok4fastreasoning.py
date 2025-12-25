import pandas as pd
import numpy as np
from typing import List, Optional

class Solution:
    def solve(
        self,
        df: pd.DataFrame,
        early_stop: int = 100000,
        row_stop: int = 4,
        col_stop: int = 2,
        col_merge: Optional[List[List[str]]] = None,
        one_way_dep: Optional[List] = None,
        distinct_value_threshold: float = 0.7,
        parallel: bool = True,
    ) -> pd.DataFrame:
        if one_way_dep is not None:
            pass  # Not used in this variant

        N, _ = df.shape
        df = df.copy()

        # Apply column merges
        if col_merge is not None:
            for group in col_merge:
                if not group:
                    continue
                merged_name = 'merged_' + '_'.join(group)
                merged = df[group].astype(str).apply(lambda x: ''.join(x), axis=1)
                df[merged_name] = merged
                df = df.drop(columns=group)

        columns = list(df.columns)
        M = len(columns)
        if M == 0:
            return df

        # Precompute string array
        str_df = df[columns].astype(str)
        str_array = str_df.values  # N x M numpy array of strings

        # Greedy selection of permutation
        remaining = set(range(M))
        current_perm = []

        for step in range(M):
            best_score = -1.0
            best_cand = None
            candidates = list(remaining)

            # Compute scores for each candidate
            cand_scores = {}
            for cand in candidates:
                partial_perm = current_perm + [cand]
                score = self._compute_partial_hit_rate(str_array, partial_perm, N)
                cand_scores[cand] = score
                if score > best_score:
                    best_score = score
                    best_cand = cand

            if best_cand is None:
                break

            current_perm.append(best_cand)
            remaining.remove(best_cand)

            # Early stop check (simplified, based on steps or something)
            if len(current_perm) >= early_stop:
                break

        # If not full, append remaining in original order
        for i in remaining:
            current_perm.append(i)

        # Reorder dataframe
        ordered_columns = [columns[i] for i in current_perm]
        result_df = df[ordered_columns]

        return result_df

    def _compute_partial_hit_rate(self, str_array, perm: List[int], N: int) -> float:
        if N == 0:
            return 0.0

        d = len(perm)

        class TrieNode:
            def __init__(self):
                self.children = {}

        root = TrieNode()

        total_len = 0
        sum_lcp = 0

        def get_lcp_and_insert(row_idx: int) -> int:
            nonlocal total_len, sum_lcp
            s = ''.join(str_array[row_idx, p] for p in perm)
            total_len += len(s)

            # Traverse for LCP
            node = root
            lcp_len = 0
            i = 0
            slen = len(s)
            while i < slen:
                char = s[i]
                if char in node.children:
                    node = node.children[char]
                    i += 1
                    lcp_len += 1
                else:
                    break

            # Insert remaining
            for j in range(i, slen):
                char = s[j]
                new_node = TrieNode()
                node.children[char] = new_node
                node = new_node

            return lcp_len

        # Insert first row
        get_lcp_and_insert(0)

        # Insert remaining rows
        for i in range(1, N):
            lcp = get_lcp_and_insert(i)
            sum_lcp += lcp

        if total_len == 0:
            return 0.0

        return sum_lcp / total_len

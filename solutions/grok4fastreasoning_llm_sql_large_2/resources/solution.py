import pandas as pd
import random
from collections import Counter
from typing import List

class TrieNode:
    pass  # Not used in final direct implementation

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
        if col_merge is None:
            col_merge = []
        df = df.copy()
        merged_cols = set()
        for group in col_merge:
            if len(group) > 1 and all(c in df.columns for c in group):
                new_col = '_'.join(group)
                df[new_col] = df[group].astype(str).apply(lambda x: ''.join(x), axis=1)
                merged_cols.update(group)
        df = df.drop(columns=[c for c in merged_cols if c in df.columns])
        cols = list(df.columns)
        M = len(cols)
        if M <= 1:
            return df
        N = len(df)
        str_df = df[cols].astype(str)
        row_strs = str_df.values
        # Precompute potentials and frac_distinct
        potentials = [0.0] * M
        frac_distinct = [0.0] * M
        avg_lens = [0.0] * M
        for j in range(M):
            values = row_strs[:, j]
            counts = Counter(values)
            num_u = len(counts)
            frac_distinct[j] = num_u / N if N > 0 else 0.0
            total_count = sum(counts.values())
            if total_count > 0:
                max_c = max(counts.values()) if counts else 0
                max_freq = max_c / N
                total_l = sum(len(v) * c for v, c in counts.items())
                avg_l = total_l / N
                avg_lens[j] = avg_l
                potentials[j] = max_freq * avg_l
            else:
                potentials[j] = 0.0
        # Sample
        sample_size = min(N, row_stop * col_stop * 10)
        if sample_size < 2:
            sample_size = min(2, N)
        if N <= sample_size:
            indices = list(range(N))
        else:
            indices = sorted(random.sample(range(N), sample_size))
        sub_row_strs = row_strs[indices]
        sub_N = len(indices)
        # lcp function
        def lcp(a: str, b: str) -> int:
            i = 0
            la, lb = len(a), len(b)
            while i < la and i < lb and a[i] == b[i]:
                i += 1
            return i
        # compute_lcp_sum
        def compute_lcp_sum(perm: List[int], sub_row_strs, sub_N: int) -> int:
            if not perm:
                return 0
            partial_S = [''.join(sub_row_strs[k][j] for j in perm) for k in range(sub_N)]
            total_lcp = 0
            previous_S = []
            for ii in range(sub_N):
                if ii > 0:
                    s = partial_S[ii]
                    max_l = 0
                    for p in previous_S:
                        max_l = max(max_l, lcp(s, p))
                    total_lcp += max_l
                previous_S.append(partial_S[ii])
            return total_lcp
        # Greedy build order
        current_order = []
        remaining = list(range(M))
        for _ in range(M):
            if not remaining:
                break
            # Select candidates to try
            num_try = min(len(remaining), col_stop * 10)
            candidates_to_try = sorted(remaining, key=lambda j: -potentials[j])[:num_try]
            best_col = None
            best_lcp = -1
            for cand in candidates_to_try:
                temp_perm = current_order + [cand]
                this_lcp = compute_lcp_sum(temp_perm, sub_row_strs, sub_N)
                if this_lcp > best_lcp:
                    best_lcp = this_lcp
                    best_col = cand
            if best_col is None:
                # Fallback to highest potential
                best_col = max(remaining, key=lambda j: potentials[j])
            current_order.append(best_col)
            remaining.remove(best_col)
        # Reorder
        perm_cols = [cols[i] for i in current_order]
        df = df[perm_cols]
        return df

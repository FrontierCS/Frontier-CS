import pandas as pd
import random

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
        for group in col_merge:
            if len(group) < 2:
                continue
            merged_name = '_'.join(group)
            df[merged_name] = df[group].apply(lambda x: ''.join(str(val) for val in x), axis=1)
            df = df.drop(columns=group)
        cols = list(df.columns)
        M = len(cols)
        if M <= 1:
            return df[cols]
        N = len(df)
        col_strs = {col: [str(val) for val in df[col].values] for col in cols}
        K_sample = min(N, row_stop * 200)
        if K_sample < 2:
            K_sample = min(2, N)
        sampled = sorted(random.sample(range(N), K_sample))
        full_indices = list(range(N))

        def compute_sum_max_lcp(order, row_indices, col_strs):
            class LocalTrieNode:
                def __init__(self):
                    self.children = {}
            root = LocalTrieNode()
            total_lcp = 0
            total_len = 0
            for idx in row_indices:
                s = ''.join(col_strs[col][idx] for col in order)
                slen = len(s)
                total_len += slen
                node = root
                pos = 0
                while pos < slen and s[pos] in node.children:
                    node = node.children[s[pos]]
                    pos += 1
                total_lcp += pos
                current = node
                for p in range(pos, slen):
                    ch = s[p]
                    if ch not in current.children:
                        current.children[ch] = LocalTrieNode()
                    current = current.children[ch]
            return total_lcp, total_len

        def compute_hit_rate(order, row_indices, col_strs):
            tlcp, tlen = compute_sum_max_lcp(order, row_indices, col_strs)
            return tlcp / tlen if tlen > 0 else 0.0

        # Greedy build
        remaining = list(cols)
        current_order = []
        for _ in range(M):
            best_hit = -1.0
            best_col = None
            for cand in remaining:
                temp_order = current_order + [cand]
                hit = compute_hit_rate(temp_order, sampled, col_strs)
                if hit > best_hit:
                    best_hit = hit
                    best_col = cand
            current_order.append(best_col)
            remaining.remove(best_col)

        # Local search
        current_hit = compute_hit_rate(current_order, full_indices, col_strs)
        evals = 0
        for _ in range(col_stop):
            best_i = -1
            best_delta = 0.0
            for i in range(M - 1):
                if evals >= early_stop:
                    break
                temp_order = current_order[:]
                temp_order[i], temp_order[i + 1] = temp_order[i + 1], temp_order[i]
                temp_hit = compute_hit_rate(temp_order, full_indices, col_strs)
                evals += 1
                delta = temp_hit - current_hit
                if delta > best_delta:
                    best_delta = delta
                    best_i = i
            if best_i == -1 or best_delta <= 1e-9:
                break
            current_order[best_i], current_order[best_i + 1] = current_order[best_i + 1], current_order[best_i]
            current_hit += best_delta

        df = df[current_order]
        return df

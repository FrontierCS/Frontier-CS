import pandas as pd
import random

class TrieNode:
    def __init__(self):
        self.children = {}

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
        df = df.copy()
        if col_merge is not None:
            for group in col_merge:
                if len(group) > 1:
                    new_name = '_'.join(group)
                    df[new_name] = df.apply(lambda row: ''.join(str(row[c]) for c in group), axis=1)
                    df = df.drop(columns=group)
        all_cols = list(df.columns)
        M = len(all_cols)
        if M <= 1:
            return df
        N = len(df)
        sample_size = row_stop * 250
        R = min(N, sample_size)
        if R < 2:
            return df
        sample_indices = random.sample(range(N), R)
        str_values = [[str(df.iloc[si][all_cols[c]]) for c in range(M)] for si in sample_indices]
        beam_width = max(1, col_stop)
        current_beam = [(0.0, [])]
        total_evals = 0
        for level in range(M):
            all_possible_perms = []
            for _, perm in current_beam:
                used = set(perm)
                remaining = [j for j in range(M) if j not in used]
                for j in remaining:
                    all_possible_perms.append(perm + [j])
            extensions = []
            broke_early = False
            for new_perm in all_possible_perms:
                total_evals += 1
                if total_evals > early_stop:
                    broke_early = True
                    break
                strs = [''.join(str_values[r][j] for j in new_perm) for r in range(R)]
                total_len = sum(len(s) for s in strs)
                if total_len == 0:
                    score = 0.0
                else:
                    root = TrieNode()
                    s = strs[0]
                    node = root
                    for char in s:
                        if char not in node.children:
                            node.children[char] = TrieNode()
                        node = node.children[char]
                    sum_lcp = 0.0
                    for ii in range(1, R):
                        s = strs[ii]
                        node = root
                        depth = 0
                        for char in s:
                            if char in node.children:
                                node = node.children[char]
                                depth += 1
                            else:
                                break
                        sum_lcp += depth
                        node = root
                        for char in s:
                            if char not in node.children:
                                node.children[char] = TrieNode()
                            node = node.children[char]
                    score = sum_lcp / total_len
                extensions.append((score, new_perm))
            if broke_early:
                break
            extensions.sort(key=lambda x: x[0], reverse=True)
            current_beam = extensions[:beam_width]
        best_score, best_perm = max(current_beam, key=lambda x: x[0])
        used = set(best_perm)
        remaining = [j for j in range(M) if j not in used]
        full_perm = best_perm + remaining
        reordered_cols = [all_cols[i] for i in full_perm]
        result_df = df[reordered_cols]
        return result_df
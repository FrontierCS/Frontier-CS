import pandas as pd
import random
from typing import List, Tuple
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures

class TrieNode:
    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]

    def max_prefix_len(self, word: str) -> int:
        node = self.root
        length = 0
        for char in word:
            if char not in node.children:
                return length
            node = node.children[char]
            length += 1
        return length

def compute_hit_rate(partial_order: List[str], col_to_sample_strs: dict) -> float:
    sample_size = len(next(iter(col_to_sample_strs.values())))
    if not partial_order or sample_size < 2:
        return 0.0
    sample_strings = [''.join(col_to_sample_strs[col][j] for col in partial_order) for j in range(sample_size)]
    total_len = sum(len(s) for s in sample_strings)
    if total_len == 0:
        return 0.0
    trie = Trie()
    lcp_sum = 0
    if sample_strings:
        trie.insert(sample_strings[0])
    for s in sample_strings[1:]:
        lcp = trie.max_prefix_len(s)
        lcp_sum += lcp
        trie.insert(s)
    return lcp_sum / total_len

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
        N = len(df)
        if N == 0:
            return df.copy()
        
        df_work = df.copy()
        merged_set = set()
        if col_merge:
            for group in col_merge:
                if not group:
                    continue
                group_set = set(group)
                if group_set & merged_set:
                    continue  # skip overlap
                new_name = '_'.join(sorted(group))
                df_work[new_name] = df_work.apply(lambda row: ''.join(str(row[c]) for c in group), axis=1)
                merged_set.update(group_set)
            df_work = df_work.drop(columns=[c for c in merged_set if c in df_work.columns])
        
        columns = list(df_work.columns)
        K = len(columns)
        if K == 0 or N < 2:
            return df_work[columns]
        
        sample_size = min(N, row_stop * 500)
        if sample_size < 2:
            sample_size = 2 if N >= 2 else N
        sample_indices = random.sample(range(N), sample_size)
        
        col_to_sample_strs = {}
        for col in columns:
            col_to_sample_strs[col] = [str(df_work.iloc[idx][col]) for idx in sample_indices]
        
        beam_width = max(1, col_stop * 25)
        current_beam: List[Tuple[float, List[str]]] = [(0.0, [])]
        total_evals = 0
        best_score = -1.0
        best_order = []
        all_columns_set = set(columns)
        
        for depth in range(1, K + 1):
            partials_to_try = []
            for _, partial in current_beam:
                remaining = list(all_columns_set - set(partial))
                for next_col in remaining:
                    partials_to_try.append(partial + [next_col])
            
            num_cand = len(partials_to_try)
            total_evals += num_cand
            if total_evals > early_stop and depth < K:
                break
            
            if parallel:
                with ProcessPoolExecutor(max_workers=8) as executor:
                    futures = [executor.submit(compute_hit_rate, p, col_to_sample_strs) for p in partials_to_try]
                    scores = [f.result() for f in concurrent.futures.as_completed(futures)]
            else:
                scores = [compute_hit_rate(p, col_to_sample_strs) for p in partials_to_try]
            
            candidate_list = list(zip(scores, partials_to_try))
            candidate_list.sort(key=lambda x: x[0], reverse=True)
            current_beam = candidate_list[:beam_width]
            
            for sc, p in candidate_list:
                if sc > best_score:
                    best_score = sc
                    best_order = p
        
        if not best_order or len(best_order) < K:
            remaining = [c for c in columns if c not in set(best_order)]
            best_order += remaining
        
        result_df = df_work[best_order]
        return result_df

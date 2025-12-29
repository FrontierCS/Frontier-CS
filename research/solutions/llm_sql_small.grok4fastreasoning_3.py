import pandas as pd
import random
from typing import List, Tuple

class TrieNode:
    def __init__(self):
        self.children = {}

def compute_score(order: List[str], df_str: pd.DataFrame, sample_rows: List[int]) -> float:
    if not order:
        return 0.0
    root = TrieNode()
    total_lcp = 0.0
    Ns = len(sample_rows)
    col_indices = {col: df_str.columns.get_loc(col) for col in order}
    for idx, r in enumerate(sample_rows):
        # query
        node = root
        match_len = 0
        broke = False
        for col in order:
            seg = df_str.iat[r, col_indices[col]]
            for char in seg:
                if char in node.children:
                    node = node.children[char]
                    match_len += 1
                else:
                    broke = True
                    break
            if broke:
                break
        if idx > 0:
            total_lcp += match_len
        # insert
        node = root
        for col in order:
            seg = df_str.iat[r, col_indices[col]]
            for char in seg:
                if char not in node.children:
                    node.children[char] = TrieNode()
                node = node.children[char]
    return total_lcp

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
        if col_merge is not None:
            for group in col_merge:
                if len(group) > 0:
                    merged_name = '_'.join(group)
                    df[merged_name] = df[group].apply(lambda x: ''.join(x.astype(str).values), axis=1)
                    df = df.drop(columns=group)
        cols = list(df.columns)
        M = len(cols)
        if M <= 1:
            return df
        N = len(df)
        sample_size = min(N, row_stop * 1000)
        random.seed(42)
        sample_rows = random.sample(range(N), sample_size)
        df_str = df[cols].astype(str)
        beam_width = col_stop
        beam: List[Tuple[List[str], float]] = [([], 0.0)]
        for depth in range(M):
            candidate_tuples = set()
            for partial, _ in beam:
                remaining = [c for c in cols if c not in partial]
                for next_c in remaining:
                    new_partial = tuple(partial + [next_c])
                    candidate_tuples.add(new_partial)
            if len(candidate_tuples) > early_stop:
                candidate_tuples = set(random.sample(list(candidate_tuples), early_stop))
            scores = {}
            for t in candidate_tuples:
                scores[t] = compute_score(list(t), df_str, sample_rows)
            cand_list = sorted([(list(t), scores[t]) for t in candidate_tuples], key=lambda x: x[1], reverse=True)
            beam = cand_list[:beam_width]
        best_order, _ = max(beam, key=lambda x: x[1])
        df = df[best_order]
        return df
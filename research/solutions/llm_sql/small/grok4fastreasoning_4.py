import pandas as pd
import random
from typing import List

class TrieNode:
    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}

def compute_hit_rate(df: pd.DataFrame, order: List[str]) -> float:
    N = len(df)
    if N < 2:
        return 0.0
    sample_size = min(4096, N)
    if sample_size < 2:
        return 0.0
    if sample_size == N:
        indices = list(range(N))
    else:
        indices = random.sample(range(N), sample_size)
    indices.sort()
    strings = []
    col_indices = [df.columns.get_loc(c) for c in order]
    for idx in indices:
        row_values = df.iloc[idx, col_indices].astype(str).values
        s = ''.join(row_values)
        strings.append(s)
    total_len = sum(len(s) for s in strings)
    if total_len == 0:
        return 0.0
    sum_lcp = 0
    root = TrieNode()
    for i, s in enumerate(strings):
        if i == 0:
            node = root
            for c in s:
                if c not in node.children:
                    node.children[c] = TrieNode()
                node = node.children[c]
            continue
        node = root
        lcp_len = 0
        for c in s:
            if c in node.children:
                node = node.children[c]
                lcp_len += 1
            else:
                break
        sum_lcp += lcp_len
        for c in s[lcp_len:]:
            if c not in node.children:
                node.children[c] = TrieNode()
            node = node.children[c]
    return sum_lcp / total_len

def apply_merges(df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
    df = df.copy()
    cols_to_drop = set()
    for group in col_merge or []:
        if len(group) > 1:
            merged_name = '_'.join(group)
            df[merged_name] = df[group].apply(lambda row: ''.join(row.astype(str).values), axis=1)
            cols_to_drop.update(group)
    if cols_to_drop:
        df = df.drop(columns=list(cols_to_drop))
    return df

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
        df = apply_merges(df, col_merge)
        cols = list(df.columns)
        M = len(cols)
        if M <= 1:
            return df
        remaining = set(cols)
        current_order = []
        for _ in range(M):
            best_score = -1.0
            best_col = None
            for cand in list(remaining):
                temp_order = current_order + [cand]
                score = compute_hit_rate(df, temp_order)
                if score > best_score:
                    best_score = score
                    best_col = cand
            if best_col is not None:
                current_order.append(best_col)
                remaining.remove(best_col)
        return df[current_order]
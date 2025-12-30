import pandas as pd
import itertools
import concurrent.futures
from typing import List, Dict, Any

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]

    def max_prefix_len(self, word: str) -> int:
        node = self.root
        length = 0
        for char in word:
            if char in node.children:
                node = node.children[char]
                length += 1
            else:
                return length
        return length

def compute_sum_lcp(order: List[str], values: Dict[str, List[str]], N: int) -> int:
    total_lcp = 0
    trie = Trie()
    for i in range(N):
        s = ''.join(values[col][i] for col in order)
        if i > 0:
            max_l = trie.max_prefix_len(s)
            total_lcp += max_l
        trie.insert(s)
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
        df = df.copy()
        N = len(df)
        if col_merge is not None:
            to_drop = set()
            for group in col_merge:
                if len(group) > 1:
                    merged_name = '_'.join(group)
                    df[merged_name] = df[group].apply(lambda row: ''.join(map(str, row)), axis=1)
                    to_drop.update(group)
            if to_drop:
                df = df.drop(columns=list(to_drop))
        cols = list(df.columns)
        K = len(cols)
        if K == 0:
            return df
        str_df = df.astype(str)
        values = {col: str_df[col].tolist() for col in cols}
        low_div = []
        high_div = []
        for col in cols:
            num_distinct = str_df[col].nunique()
            div = num_distinct / N if N > 0 else 0
            if div <= distinct_value_threshold:
                low_div.append(col)
            else:
                high_div.append(col)
        best_order = []
        remaining = set(low_div)
        num_evals = 0
        while remaining and num_evals < early_stop:
            look = min(col_stop, len(remaining))
            candidates = list(itertools.permutations(remaining, look))
            candidate_orders = [best_order + list(seq) for seq in candidates]
            best_score = -1
            best_full_order = None
            if parallel and len(candidate_orders) > 1:
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    future_to_order = {executor.submit(compute_sum_lcp, order, values, N): order for order in candidate_orders}
                    for future in concurrent.futures.as_completed(future_to_order):
                        if num_evals >= early_stop:
                            break
                        try:
                            score = future.result()
                            num_evals += 1
                            if score > best_score:
                                best_score = score
                                best_full_order = future_to_order[future]
                        except Exception:
                            pass
            else:
                for order in candidate_orders:
                    if num_evals >= early_stop:
                        break
                    score = compute_sum_lcp(order, values, N)
                    num_evals += 1
                    if score > best_score:
                        best_score = score
                        best_full_order = order
            if best_full_order is None:
                break
            new_added = best_full_order[len(best_order):]
            best_order = best_full_order
            for c in new_added:
                remaining.discard(c)
        if remaining:
            # append any leftover low div in arbitrary order
            best_order += list(remaining)
        # append high div sorted by increasing nunique
        high_sorted = sorted(high_div, key=lambda c: str_df[c].nunique())
        best_order += high_sorted
        return df[best_order]
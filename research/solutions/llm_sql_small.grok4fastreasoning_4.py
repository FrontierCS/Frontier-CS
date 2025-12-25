import pandas as pd
import random
from typing import List, Dict, Tuple
import multiprocessing as mp

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}

def insert_and_get_lcp(s: str, root: TrieNode) -> int:
    node = root
    lcp_len = 0
    for char in s:
        if char in node.children:
            node = node.children[char]
            lcp_len += 1
        else:
            break
    else:
        lcp_len = len(s)
    # Insert the remaining part
    current = node
    for j in range(lcp_len, len(s)):
        ch = s[j]
        if ch not in current.children:
            current.children[ch] = TrieNode()
        current = current.children[ch]
    return lcp_len

def compute_hit_rate_strs(col_strs: Dict[str, List[str]], order: List[str], num_samples: int) -> float:
    strings = []
    total_len = 0
    for r in range(num_samples):
        row_str = "".join(col_strs[c][r] for c in order)
        strings.append(row_str)
        total_len += len(row_str)
    if total_len == 0:
        return 0.0
    root = TrieNode()
    prefix_sum = 0
    insert_and_get_lcp(strings[0], root)
    for s in strings[1:]:
        prefix_sum += insert_and_get_lcp(s, root)
    return prefix_sum / total_len

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
        current_cols = list(df.columns)
        N = len(df)
        if N <= 1:
            return df
        
        if col_merge is not None:
            merged_groups = []
            for group in col_merge:
                if not group:
                    continue
                merged_name = '_'.join(group)
                df[merged_name] = df[group].apply(lambda x: ''.join(x.astype(str)), axis=1)
                merged_groups.append(merged_name)
                df.drop(columns=group, inplace=True)
            current_cols = list(df.columns)
        
        frac_dict = {col: df[col].nunique() / N for col in current_cols}
        
        sample_size = min(N, row_stop * 500)
        if sample_size < N:
            sample_rows = random.sample(range(N), sample_size)
        else:
            sample_rows = list(range(N))
        
        col_strs = {col: [str(df.iloc[i][col]) for i in sample_rows] for col in current_cols}
        num_samples = len(sample_rows)
        
        beam_width = 10
        beam: List[Tuple[float, List[str]]] = [(0.0, [])]
        total_evals = 0
        
        for _ in range(len(current_cols)):
            new_orders_to_eval = []
            for _, partial_order in beam:
                remaining = [c for c in current_cols if c not in partial_order]
                remaining.sort(key=lambda c: frac_dict[c])
                for cand in remaining:
                    new_orders_to_eval.append(partial_order + [cand])
            
            num_to_eval = len(new_orders_to_eval)
            total_evals += num_to_eval
            if total_evals > early_stop:
                break
            
            if parallel and num_to_eval > 1:
                with mp.Pool(processes=min(8, mp.cpu_count())) as pool:
                    scores = pool.starmap(
                        compute_hit_rate_strs,
                        [(col_strs, ord_, num_samples) for ord_ in new_orders_to_eval]
                    )
            else:
                scores = [
                    compute_hit_rate_strs(col_strs, ord_, num_samples)
                    for ord_ in new_orders_to_eval
                ]
            
            new_beam = list(zip(scores, new_orders_to_eval))
            new_beam.sort(key=lambda x: x[0], reverse=True)
            beam = new_beam[:beam_width]
            if len(beam) == 0:
                break
        
        if beam:
            best_order = max(beam, key=lambda x: x[0])[1]
        else:
            best_order = current_cols  # fallback
        
        return df[best_order]

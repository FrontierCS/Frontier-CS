import pandas as pd
import random
import multiprocessing as mp
import os

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
        if one_way_dep is not None:
            pass
        df = df.copy()
        if col_merge:
            for group in col_merge:
                if len(group) > 1:
                    merged_name = '_'.join(group)
                    temp = df[group].astype(str)
                    merged = temp.apply(lambda x: ''.join(x), axis=1)
                    df[merged_name] = merged
                    df = df.drop(columns=group)
        current_columns = list(df.columns)
        M = len(current_columns)
        if M == 0:
            return pd.DataFrame()
        N = len(df)
        str_values = df.astype(str).values
        col_to_idx = {col: idx for idx, col in enumerate(current_columns)}
        sample_size = min(N, row_stop * 64)
        sample_indices = sorted(random.sample(range(N), sample_size)) if sample_size < N else list(range(N))
        sample_str_rows = [list(str_values[si]) for si in sample_indices]
        num_sample = len(sample_str_rows)
        beam_size = max(1, col_stop)
        beam = [([], 0.0)]
        total_evals = 0
        num_workers = min(8, os.cpu_count() or 1) if parallel else 1

        def worker(args):
            perm, sample_str_rows, col_to_idx, num_sample = args
            p = [col_to_idx[col] for col in perm]
            total_lcp = 0
            total_len = 0.0
            root = TrieNode()
            for idx in range(num_sample):
                row_str = ''.join(sample_str_rows[idx][j] for j in p)
                l = len(row_str)
                total_len += l
                if idx == 0:
                    node = root
                    for ch in row_str:
                        if ch not in node.children:
                            node.children[ch] = TrieNode()
                        node = node.children[ch]
                    continue
                node = root
                i = 0
                l_str = len(row_str)
                while i < l_str and row_str[i] in node.children:
                    node = node.children[row_str[i]]
                    i += 1
                total_lcp += i
                curr_node = node
                for k in range(i, l_str):
                    ch = row_str[k]
                    if ch not in curr_node.children:
                        curr_node.children[ch] = TrieNode()
                    curr_node = curr_node.children[ch]
            return total_lcp / total_len if total_len > 0 else 0.0

        for step in range(M):
            all_cand = []
            for partial_perm, _ in beam:
                used = set(partial_perm)
                avail = [col for col in current_columns if col not in used]
                for col in avail:
                    all_cand.append(partial_perm + [col])
            num_new_evals = len(all_cand)
            if total_evals + num_new_evals > early_stop:
                best_perm = max(beam, key=lambda x: x[1])[0]
                break
            args_list = [(perm, sample_str_rows, col_to_idx, num_sample) for perm in all_cand]
            if parallel and num_workers > 1 and num_new_evals > 0:
                with mp.Pool(num_workers) as pool:
                    scores = pool.map(worker, args_list)
            else:
                scores = [worker(arg) for arg in args_list]
            total_evals += num_new_evals
            scored_cand = sorted(zip(all_cand, scores), key=lambda x: x[1], reverse=True)
            beam = scored_cand[:beam_size]
        else:
            best_perm = beam[0][0]
        return df[best_perm].copy()

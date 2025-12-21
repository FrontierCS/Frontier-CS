import pandas as pd
import math
from multiprocessing import Pool, cpu_count
from functools import partial
import sys

# It's better to put helper functions outside the class for multiprocessing pickling
def _calculate_lcp_sum_for_strings(strings: list[str]) -> int:
    """Calculates the total LCP sum using a Trie."""
    trie = {}
    total_lcp = 0
    if not strings:
        return 0
        
    for s in strings:
        if not s:
            continue
        node = trie
        lcp = 0
        i = 0
        s_len = len(s)
        while i < s_len:
            char = s[i]
            if char in node:
                node = node[char]
                lcp += 1
                i += 1
            else:
                break
        
        total_lcp += lcp
        
        # Insert the rest of the string
        while i < s_len:
            char = s[i]
            node[char] = {}
            node = node[char]
            i += 1
            
    return total_lcp

def _score_candidate_expansion(args):
    """
    Worker function for parallel scoring.
    It computes new strings and their LCP sum.
    """
    p, c, base_strings, data_c = args
    new_strings = [base + val for base, val in zip(base_strings, data_c)]
    score = _calculate_lcp_sum_for_strings(new_strings)
    return score, p + [c], new_strings


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
        
        # 1. Handle Column Merges
        if col_merge:
            merged_df = df.copy()
            for i, group in enumerate(col_merge):
                if not isinstance(group, list) or not group:
                    continue
                # Ensure all columns in group exist in the dataframe
                group = [c for c in group if c in merged_df.columns]
                if not group:
                    continue
                
                new_col_name = f"_merged_{'_'.join(group)}"
                merged_df[new_col_name] = merged_df[group].astype(str).agg(''.join, axis=1)
                merged_df = merged_df.drop(columns=group)
        else:
            merged_df = df
        
        all_cols = list(merged_df.columns)
        if len(all_cols) <= 1:
            return merged_df

        # 2. Data Preparation
        # Cap early_stop to a reasonable value to manage runtime
        sample_size = min(len(merged_df), early_stop, 5000)
        if sample_size == 0:
            return merged_df
            
        sampled_df = merged_df.head(sample_size)
        
        # 3. Column Classification
        id_cols = []
        candidate_cols = []
        
        for col in all_cols:
            try:
                # Use dropna() to handle potential NaNs that break nunique() in some pandas versions
                distinct_count = sampled_df[col].dropna().nunique()
            except TypeError: # For unhashable types
                distinct_count = len(set(map(str, sampled_df[col].dropna())))

            distinct_ratio = distinct_count / sample_size
            if distinct_ratio > distinct_value_threshold and len(all_cols) > col_stop:
                id_cols.append(col)
            else:
                candidate_cols.append(col)
        
        if id_cols:
            id_col_cardinalities = {c: sampled_df[c].nunique() for c in id_cols}
            id_cols.sort(key=lambda c: id_col_cardinalities.get(c, 0), reverse=True)

        if not candidate_cols:
            return merged_df[id_cols]

        # Convert sampled data to a more accessible format for the search
        data_dict = {col: sampled_df[col].astype(str).tolist() for col in candidate_cols}

        # 4. Beam Search for `candidate_cols`
        beam = [([], [""] * sample_size)]  # (permutation, current_strings)
        num_cand_cols = len(candidate_cols)

        for k in range(num_cand_cols):
            expansion_args = []
            for p, p_strings in beam:
                remaining_cols = [c for c in candidate_cols if c not in p]
                for c in remaining_cols:
                    expansion_args.append((p, c, p_strings, data_dict[c]))

            if not expansion_args:
                break
                
            if parallel and len(expansion_args) > 1:
                num_processes = min(cpu_count(), len(expansion_args))
                with Pool(processes=num_processes) as pool:
                    scored_candidates = pool.map(_score_candidate_expansion, expansion_args)
            else:
                scored_candidates = [_score_candidate_expansion(args) for args in expansion_args]
            
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            
            beam_width = col_stop if k < num_cand_cols - 1 else 1
            beam = [(p, strings) for score, p, strings in scored_candidates[:beam_width]]

        best_p = beam[0][0] if beam and beam[0] else []
        final_permutation = best_p + id_cols

        return merged_df[final_permutation]

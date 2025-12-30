import pandas as pd
import random

def lcp(a, b):
    m = min(len(a), len(b))
    for i in range(m):
        if a[i] != b[i]:
            return i
    return m

def get_score(temp_perm, sample_idx, col_loc, str_df):
    partials = []
    for r in sample_idx:
        row_strs = [str_df.iloc[r, col_loc[c]] for c in temp_perm]
        partials.append(''.join(row_strs))
    total = 0
    S = len(sample_idx)
    for ii in range(1, S):
        si = partials[ii]
        maxl = 0
        for jj in range(ii):
            sj = partials[jj]
            l = lcp(si, sj)
            if l > maxl:
                maxl = l
        total += maxl
    return total

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
        current_cols = list(df.columns)
        for group in col_merge:
            if not group:
                continue
            merged_name = '_'.join(group)
            if all(c in current_cols for c in group):
                df[merged_name] = df[group].astype(str).apply(lambda row: ''.join(row), axis=1)
                df = df.drop(columns=group)
        columns = list(df.columns)
        N = len(df)
        if N < 2 or len(columns) == 0:
            return df
        str_df = df.astype(str)
        diversity = {c: str_df[c].nunique() / N for c in columns}
        col_loc = {c: str_df.columns.get_loc(c) for c in columns}
        S = row_stop * 25
        if S > N:
            S = N
        sample_idx = random.sample(range(N), S)
        sample_idx.sort()
        remaining = list(columns)
        perm = []
        M = len(columns)
        while remaining:
            num_try = col_stop * 10 + 10 if len(remaining) > 20 else len(remaining)
            candidates_to_try = sorted(remaining, key=lambda c: diversity[c])[:num_try]
            best_score = -1
            best_cand = None
            for cand in candidates_to_try:
                temp_perm = perm + [cand]
                score = get_score(temp_perm, sample_idx, col_loc, str_df)
                if score > best_score:
                    best_score = score
                    best_cand = cand
            if best_cand is None:
                best_cand = remaining[0]
            perm.append(best_cand)
            remaining.remove(best_cand)
        df = df[perm]
        return df
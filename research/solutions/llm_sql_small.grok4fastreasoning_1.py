import pandas as pd
import random

def lcp(s1, s2):
    minlen = min(len(s1), len(s2))
    for i in range(minlen):
        if s1[i] != s2[i]:
            return i
    return minlen

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
            pass  # not used

        # Handle column merges
        if col_merge is not None:
            for group in col_merge:
                if len(group) > 0:
                    merged_name = '_'.join(group)
                    df[merged_name] = df.apply(lambda r: ''.join(str(r[c]) for c in group), axis=1)
                    df = df.drop(columns=group)

        cols = list(df.columns)
        if not cols:
            return df

        M = len(cols)

        # Compute diversity
        div = {}
        for c in cols:
            unique = df[c].nunique()
            div[c] = unique / len(df)

        # Sort key for remaining: increasing diversity, then original index
        orig_index = {c: i for i, c in enumerate(cols)}
        def sort_remaining(remaining):
            return sorted(remaining, key=lambda c: (div[c], orig_index[c]))

        # Sample size
        S = row_stop * 25
        if S > len(df):
            S = len(df)
        if S < 2:
            order = sorted(cols, key=lambda c: (div[c], orig_index[c]))
            return df[order]

        # Sample rows
        sample_indices = random.sample(range(len(df)), S)
        sample_df = df.iloc[sample_indices].reset_index(drop=True)
        N_sample = len(sample_df)

        # Beam search parameters
        beam_size = row_stop * 5  # Adjustable based on row_stop, default 20
        total_evals = 0

        # Initial beam: empty partial
        current_beam = [([], 0.0)]

        for depth in range(M):
            candidates = []
            for partial, _ in current_beam[:beam_size]:
                remaining = set(cols) - set(partial)
                for cand in remaining:
                    new_partial = partial + [cand]
                    rem = remaining - {cand}
                    suffix = sort_remaining(rem)
                    eval_order = new_partial + suffix

                    # Compute score
                    strings = [''.join(str(row[c]) for c in eval_order) for _, row in sample_df.iterrows()]
                    total_len = sum(len(s) for s in strings)
                    if total_len == 0:
                        sc = 0.0
                    else:
                        sum_lcp = 0
                        for i in range(1, N_sample):
                            maxl = 0
                            si = strings[i]
                            for j in range(i):
                                maxl = max(maxl, lcp(si, strings[j]))
                            sum_lcp += maxl
                        sc = sum_lcp / total_len

                    candidates.append((new_partial, sc))
                    total_evals += 1
                    if total_evals >= early_stop:
                        break
                if total_evals >= early_stop:
                    break

            if total_evals >= early_stop:
                break

            # Select top beam
            candidates.sort(key=lambda x: x[1], reverse=True)
            current_beam = candidates[:beam_size]

        # Get best
        if current_beam:
            best_partial, _ = max(current_beam, key=lambda x: x[1])
            remaining = set(cols) - set(best_partial)
            best_order = best_partial + sort_remaining(remaining)
        else:
            best_order = sorted(cols, key=lambda c: (div[c], orig_index[c]))

        # Reorder DataFrame
        df_reordered = df[best_order]
        return df_reordered
import pandas as pd
import os
from os.path import commonprefix
from typing import List, Tuple

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
        # Ignore one_way_dep as per specification
        if one_way_dep is not None:
            pass

        # Apply column merges
        df = df.copy()
        used_cols = set()
        for group in col_merge or []:
            group = [c for c in group if c in df.columns and c not in used_cols]
            if len(group) > 1:
                merged_name = '_'.join(sorted(group))
                df[merged_name] = df.apply(lambda row: ''.join(str(row[c]) for c in group), axis=1)
                used_cols.update(group)

        # Drop used original columns
        df = df.drop(columns=list(used_cols), errors='ignore')

        # Columns to reorder
        columns = list(df.columns)
        M = len(columns)
        if M <= 1:
            return df

        N = len(df)

        # Precompute max_freq for heuristic
        max_freq = {}
        for col in columns:
            counts = df[col].astype(str).value_counts()
            max_freq[col] = counts.max() / N if len(counts) > 0 else 0.0

        # Sample size
        if N <= 1024:
            sample_size = N
        else:
            sample_size = 256
        if sample_size < 2:
            # Sort all by max_freq descending
            columns.sort(key=lambda c: max_freq[c], reverse=True)
            return df[columns]

        sample_df = df.iloc[:sample_size]

        # Beam search parameters
        beam_size = max(1, col_stop)

        # Initial beam: (order, used_set, score)
        beam: List[Tuple[List[str], set, float]] = [([], set(), 0.0)]

        total_evals = 0

        for depth in range(1, M + 1):
            new_beam = []
            partials = []
            for order, used, _ in beam:
                remaining = [c for c in columns if c not in used]
                partials.append((order, used, remaining))

            all_extensions = []
            for order, used, remaining in partials:
                for cand in remaining:
                    temp_order = order + [cand]
                    temp_used = used | {cand}

                    # Compute temp_strings
                    temp_strings = [
                        ''.join(str(sample_df.iloc[r][col]) for col in temp_order)
                        for r in range(sample_size)
                    ]

                    # Compute sum_lcp
                    partial_sum_lcp = 0
                    for i in range(1, sample_size):
                        si = temp_strings[i]
                        max_l = 0
                        for j in range(i):
                            sj = temp_strings[j]
                            lcp_len = len(commonprefix((si, sj)))
                            if lcp_len > max_l:
                                max_l = lcp_len
                        partial_sum_lcp += max_l

                    partial_total_len = sum(len(s) for s in temp_strings)
                    new_score = partial_sum_lcp / partial_total_len if partial_total_len > 0 else 0.0

                    all_extensions.append((temp_order, temp_used, new_score))
                    total_evals += 1

                    if total_evals > early_stop:
                        break
                if total_evals > early_stop:
                    break
            if total_evals > early_stop:
                break

            # Select top beam_size
            all_extensions.sort(key=lambda x: x[2], reverse=True)
            beam = all_extensions[:beam_size]

        # Get best order
        best_order, _, _ = beam[0]

        # If not full (due to early stop), add remaining sorted by max_freq
        if len(best_order) < M:
            remaining = [c for c in columns if c not in set(best_order)]
            remaining.sort(key=lambda c: max_freq[c], reverse=True)
            best_order += remaining

        # Reorder df
        result_df = df[best_order]

        return result_df

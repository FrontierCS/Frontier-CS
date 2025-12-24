import pandas as pd
import random

class Solution:
    def _compute_hit_rate(self, col_strs, order, sample_size):
        strings = [''.join(col_strs[col][r] for col in order) for r in range(sample_size)]
        total_len = sum(len(s) for s in strings)
        if total_len == 0:
            return 0.0

        class TrieNode:
            def __init__(self):
                self.children = {}

        root = TrieNode()
        numerator = 0
        for s in strings:
            node = root
            lcp = 0
            i = 0
            while i < len(s) and s[i] in node.children:
                node = node.children[s[i]]
                i += 1
                lcp += 1
            numerator += lcp
            for j in range(i, len(s)):
                ch = s[j]
                if ch not in node.children:
                    node.children[ch] = TrieNode()
                node = node.children[ch]
        hit_rate = numerator / total_len
        return hit_rate

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
        if col_merge is not None:
            to_drop = set()
            for group in col_merge:
                group = list(group)
                if len(group) <= 1:
                    continue
                def concat_row(row):
                    return ''.join(str(row[col]) for col in group)
                merged = df[group].apply(concat_row, axis=1)
                new_name = '|'.join(group)
                df[new_name] = merged
                to_drop.update(group)
            if to_drop:
                df = df.drop(columns=list(to_drop))

        all_cols = list(df.columns)
        M = len(all_cols)
        if M <= 1:
            return df[all_cols]

        N = len(df)
        sample_size = min(row_stop * 500, N)
        if sample_size < N:
            sample_idx = random.sample(range(N), sample_size)
            sample_df = df.iloc[sample_idx].reset_index(drop=True)
        else:
            sample_df = df
            sample_size = N

        col_strs = {}
        for col in all_cols:
            col_strs[col] = [str(val) for val in sample_df[col]]

        beam_width = max(1, col_stop * 2)

        # Initial beam with single columns
        single_scores = []
        for col in all_cols:
            score = self._compute_hit_rate(col_strs, [col], sample_size)
            single_scores.append(([col], score))
        single_scores.sort(key=lambda x: x[1], reverse=True)
        current_beam = single_scores[:beam_width]

        total_evals = len(all_cols)
        for depth in range(1, M):
            if total_evals >= early_stop:
                break
            candidates = []
            for partial, _ in current_beam:
                remaining = [c for c in all_cols if c not in partial]
                for next_col in remaining:
                    new_partial = partial + [next_col]
                    new_score = self._compute_hit_rate(col_strs, new_partial, sample_size)
                    candidates.append((new_partial, new_score))
                    total_evals += 1
                    if total_evals >= early_stop:
                        break
                if total_evals >= early_stop:
                    break
            if total_evals >= early_stop:
                break
            candidates.sort(key=lambda x: x[1], reverse=True)
            current_beam = candidates[:beam_width]

        if current_beam:
            best_order = current_beam[0][0]
        else:
            best_order = all_cols

        result_df = df[best_order]
        return result_df

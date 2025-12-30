import pandas as pd

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
        if col_merge is not None:
            cols_to_drop = set()
            for i, group in enumerate(col_merge):
                if isinstance(group, (list, tuple)) and len(group) > 1:
                    if all(col in df.columns for col in group):
                        merged_name = f"merged_{i}"
                        j = i
                        while merged_name in df.columns:
                            j += 1
                            merged_name = f"merged_{j}"
                        merged_series = df[group].apply(lambda row: ''.join(row.astype(str)), axis=1)
                        df[merged_name] = merged_series
                        cols_to_drop.update(group)
            if cols_to_drop:
                df = df.drop(columns=list(cols_to_drop))

        all_cols = list(df.columns)
        if len(all_cols) == 0:
            return df

        N = len(df)
        unique_cols = [col for col in all_cols if df[col].nunique() / N > distinct_value_threshold]
        non_unique_cols = [col for col in all_cols if df[col].nunique() / N <= distinct_value_threshold]

        def lcp(a: str, b: str) -> int:
            i = 0
            min_len = min(len(a), len(b))
            while i < min_len and a[i] == b[i]:
                i += 1
            return i

        def compute_score(perm: list, df_sample: pd.DataFrame, row_sample_size: int) -> float:
            partial_strs = []
            for i in range(row_sample_size):
                row_series = df_sample[perm].iloc[i].astype(str)
                s = ''.join(row_series.values)
                partial_strs.append(s)
            total_lcp = 0.0
            total_len = len(partial_strs[0])
            for i in range(1, row_sample_size):
                si = partial_strs[i]
                total_len += len(si)
                max_lcp_len = 0
                for j in range(i):
                    sj = partial_strs[j]
                    curr_lcp = lcp(si, sj)
                    if curr_lcp > max_lcp_len:
                        max_lcp_len = curr_lcp
                total_lcp += max_lcp_len
            if total_len == 0:
                return 0.0
            return total_lcp / total_len

        if len(non_unique_cols) == 0:
            return df[all_cols]

        row_sample_size = min(row_stop, len(df))
        if row_sample_size < 2:
            full_order = non_unique_cols + unique_cols
            return df[full_order]

        df_sample = df.iloc[:row_sample_size]

        # Beam search on non_unique_cols
        search_cols = non_unique_cols
        M = len(search_cols)
        beam_width = max(1, col_stop)
        beam = [(0.0, [])]
        eval_count = 0

        for depth in range(M):
            new_beam = []
            for _, partial_perm in beam:
                remaining = [c for c in search_cols if c not in partial_perm]
                for cand in remaining:
                    new_perm = partial_perm + [cand]
                    sc = compute_score(new_perm, df_sample, row_sample_size)
                    new_beam.append((sc, new_perm))
                    eval_count += 1
                    if eval_count >= early_stop:
                        break
                if eval_count >= early_stop:
                    break
            if eval_count >= early_stop:
                break
            new_beam.sort(key=lambda x: x[0], reverse=True)
            beam = new_beam[:beam_width]

        best_perm = beam[0][1]
        full_order = best_perm + unique_cols
        return df[full_order]
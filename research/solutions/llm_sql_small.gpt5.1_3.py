import pandas as pd
import numpy as np


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge) -> pd.DataFrame:
        if col_merge is None:
            return df

        df_merged = df.copy()
        for group in col_merge:
            if group is None:
                continue

            # Normalize group to list
            if isinstance(group, (str, int)):
                raw_list = [group]
            else:
                try:
                    raw_list = list(group)
                except TypeError:
                    raw_list = [group]

            group_cols = []
            for x in raw_list:
                # Prefer explicit string column names
                if isinstance(x, str) and x in df_merged.columns:
                    if x not in group_cols:
                        group_cols.append(x)
                elif isinstance(x, int):
                    # Try 0-based index
                    if 0 <= x < len(df_merged.columns):
                        name = df_merged.columns[x]
                        if name not in group_cols:
                            group_cols.append(name)
                    # Fallback: 1-based index
                    elif 1 <= x <= len(df_merged.columns):
                        name = df_merged.columns[x - 1]
                        if name not in group_cols:
                            group_cols.append(name)
                else:
                    sx = str(x)
                    if sx in df_merged.columns and sx not in group_cols:
                        group_cols.append(sx)

            # Only merge if at least two existing columns are in the group
            if len(group_cols) <= 1:
                continue

            base_name = "MERGED_" + "_".join(map(str, group_cols))
            new_name = base_name
            suffix = 1
            while new_name in df_merged.columns:
                new_name = f"{base_name}_{suffix}"
                suffix += 1

            merged_series = df_merged[group_cols].astype(str).agg("".join, axis=1)
            df_merged = df_merged.drop(columns=group_cols)
            df_merged[new_name] = merged_series

        return df_merged

    @staticmethod
    def _lcp_len_strings(a: str, b: str) -> int:
        limit = min(len(a), len(b))
        i = 0
        while i < limit and a[i] == b[i]:
            i += 1
        return i

    def _approx_order_score(self, order, col_sample_vals) -> float:
        if not order or not col_sample_vals:
            return 0.0

        # All value lists have same length
        any_col = next(iter(col_sample_vals))
        sample_size = len(col_sample_vals[any_col])
        if sample_size <= 1:
            return 0.0

        # Build concatenated strings for each sampled row
        S = [
            "".join(col_sample_vals[col][r] for col in order)
            for r in range(sample_size)
        ]

        S.sort()
        total_lcp = 0
        prev = S[0]
        for s in S[1:]:
            total_lcp += self._lcp_len_strings(prev, s)
            prev = s
        return float(total_lcp)

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
        # Step 1: apply column merges
        df_work = df.copy()
        if col_merge is not None and len(col_merge) > 0:
            df_work = self._apply_col_merge(df_work, col_merge)

        num_cols = df_work.shape[1]
        num_rows = df_work.shape[0]

        if num_cols <= 1 or num_rows <= 1:
            return df_work

        # String view for statistics and scoring
        df_str = df_work.astype(str)
        columns = list(df_str.columns)
        N = num_rows
        denom_pairs = N * (N - 1) if N > 1 else 1

        # Sampling for per-column adjacency LCP statistics
        max_sample_stats = 3000
        sample_n_stats = min(N, max_sample_stats)
        if sample_n_stats <= 1:
            sample_idx_stats = np.arange(sample_n_stats)
        else:
            sample_idx_stats = np.linspace(0, N - 1, sample_n_stats, dtype=int)

        col_stats = []

        for col in columns:
            s_col = df_str[col]

            # Average string length
            lengths = s_col.str.len()
            avg_len = float(lengths.mean()) if N > 0 else 0.0

            # Equality probability via value counts
            vc = s_col.value_counts(dropna=False, sort=False)
            counts = vc.values.astype("int64")
            num_unique = len(vc)

            if N > 1:
                same_pairs = int((counts * (counts - 1)).sum())
                same_prob = same_pairs / denom_pairs
            else:
                same_prob = 1.0

            if same_prob < 0.0:
                same_prob = 0.0
            elif same_prob > 1.0:
                same_prob = 1.0

            distinct_ratio = num_unique / N if N > 0 else 0.0

            # Approximate mean adjacent LCP on a sample of this column
            if sample_n_stats > 1 and avg_len > 0.0:
                sample_vals = s_col.iloc[sample_idx_stats].tolist()
                sample_vals.sort()
                total_lcp = 0
                prev = sample_vals[0]
                for v in sample_vals[1:]:
                    total_lcp += self._lcp_len_strings(prev, v)
                    prev = v
                adj_lcp_mean = total_lcp / (sample_n_stats - 1)
            else:
                adj_lcp_mean = 0.0

            eq_score = same_prob * avg_len
            base = eq_score + 0.1 * adj_lcp_mean

            # Penalize very high-cardinality columns
            if distinct_ratio > distinct_value_threshold:
                base *= 0.5

            if same_prob >= 1.0 - 1e-9:
                priority = float("inf")
            else:
                priority = base / (1.0 - same_prob + 1e-9)

            col_stats.append((col, priority, same_prob, avg_len))

        # Initial heuristic ordering
        col_stats.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        order = [c[0] for c in col_stats]

        # Prepare shared samples for approximate permutation scoring
        max_sample_order = 2000
        sample_n_order = min(N, max_sample_order)
        if sample_n_order <= 1:
            # Not enough rows to benefit from reordering
            return df_work.loc[:, order]

        if sample_n_order == N:
            sample_idx_order = np.arange(N)
        else:
            sample_idx_order = np.linspace(0, N - 1, sample_n_order, dtype=int)

        col_sample_vals = {
            col: df_str[col].iloc[sample_idx_order].tolist() for col in columns
        }

        # Local search (pairwise swap hill-climbing) on approximate score
        best_order = order[:]
        best_score = self._approx_order_score(best_order, col_sample_vals)
        eval_count = 1
        max_iterations = max(1, col_stop * num_cols)

        for _ in range(max_iterations):
            improved = False
            m = len(best_order)
            current_order = best_order

            for i in range(m):
                for j in range(i + 1, m):
                    if eval_count >= early_stop:
                        break
                    candidate = current_order[:]
                    candidate[i], candidate[j] = candidate[j], candidate[i]
                    score = self._approx_order_score(candidate, col_sample_vals)
                    eval_count += 1
                    if score > best_score:
                        best_score = score
                        best_order = candidate
                        improved = True
                if eval_count >= early_stop:
                    break
            if not improved or eval_count >= early_stop:
                break

        return df_work.loc[:, best_order]

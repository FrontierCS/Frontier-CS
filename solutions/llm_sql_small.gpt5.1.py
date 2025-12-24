import pandas as pd
import math


class Solution:
    def _compute_column_metrics(self, values, max_prefix_len):
        """
        Compute:
        - E_lcp: expected longest common prefix length between two random values from this column
        - p_full_eq: probability that two random values are exactly equal
        """
        n = len(values)
        if n == 0:
            return 0.0, 0.0

        full_counts = {}
        max_len = 0
        for s in values:
            ls = len(s)
            if ls > max_len:
                max_len = ls
            full_counts[s] = full_counts.get(s, 0) + 1

        n2 = n * n
        sum_sq = 0
        for c in full_counts.values():
            sum_sq += c * c
        p_full_eq = sum_sq / n2 if n2 > 0 else 0.0

        max_l = min(max_len, max_prefix_len)
        if max_l == 0 or n2 == 0:
            return 0.0, p_full_eq

        prefix_counts = [None] * (max_l + 1)
        for l in range(1, max_l + 1):
            prefix_counts[l] = {}

        for s in values:
            ls = len(s)
            upto = max_l if ls >= max_l else ls
            prefix = ""
            for l in range(1, upto + 1):
                prefix += s[l - 1]
                d = prefix_counts[l]
                d[prefix] = d.get(prefix, 0) + 1

        e_lcp = 0.0
        for l in range(1, max_l + 1):
            d = prefix_counts[l]
            if not d:
                break
            sum_sq_l = 0
            for cnt in d.values():
                sum_sq_l += cnt * cnt
            p_l = sum_sq_l / n2
            e_lcp += p_l

        return e_lcp, p_full_eq

    def _apply_column_merges(self, df, col_merge):
        if not col_merge:
            return df

        df_work = df.copy()
        orig_cols = list(df_work.columns)

        def resolve_col(x):
            if isinstance(x, int):
                if 0 <= x < len(orig_cols):
                    return orig_cols[x]
                return None
            else:
                return x if x in orig_cols else None

        used = set()
        resolved_groups = []
        for group in col_merge:
            if not group:
                continue
            names = []
            for item in group:
                name = resolve_col(item)
                if name is None:
                    continue
                if name in used:
                    continue
                if name in orig_cols:
                    used.add(name)
                    names.append(name)
            if len(names) >= 2:
                resolved_groups.append(names)

        for group_cols in resolved_groups:
            current_cols = list(df_work.columns)
            indices = [df_work.columns.get_loc(c) for c in group_cols if c in df_work.columns]
            if not indices:
                continue
            insert_at = min(indices)
            base_name = "MERGED_" + "_".join(str(c) for c in group_cols)
            new_name = base_name
            suffix = 1
            while new_name in df_work.columns:
                new_name = f"{base_name}_{suffix}"
                suffix += 1
            new_series = df_work[group_cols].astype(str).agg(''.join, axis=1)
            df_work = df_work.drop(columns=group_cols)
            df_work.insert(insert_at, new_name, new_series)

        return df_work

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
        df_work = self._apply_column_merges(df, col_merge)

        n_rows, n_cols = df_work.shape
        if n_cols <= 1 or n_rows <= 1:
            return df_work

        # Step 2: convert all values to string for analysis
        str_df = df_work.astype(str)
        columns = list(str_df.columns)
        m = len(columns)

        # Step 3: compute per-column metrics
        max_prefix_len = 32
        e_lcp_list = [0.0] * m
        p_full_list = [0.0] * m

        for idx, col in enumerate(columns):
            col_values = str_df[col].tolist()
            e_lcp, p_full = self._compute_column_metrics(col_values, max_prefix_len)
            e_lcp_list[idx] = e_lcp
            p_full_list[idx] = p_full

        # Step 4: dynamic programming over subsets to find best order
        size = 1 << m
        dp = [0.0] * size
        prod_p = [1.0] * size
        last_idx = [-1] * size

        # Precompute product of p_full for each subset
        for mask in range(1, size):
            lsb = mask & -mask
            idx = lsb.bit_length() - 1
            prev = mask ^ lsb
            prod_p[mask] = prod_p[prev] * p_full_list[idx]

        # DP to compute best score for each subset
        for mask in range(1, size):
            best_score = -1e100
            best_col = -1
            sub = mask
            while sub:
                lsb = sub & -sub
                j = lsb.bit_length() - 1
                prev = mask ^ lsb
                val = dp[prev] + prod_p[prev] * e_lcp_list[j]
                if val > best_score:
                    best_score = val
                    best_col = j
                sub ^= lsb
            if best_col == -1:
                best_score = 0.0
            dp[mask] = best_score
            last_idx[mask] = best_col

        # Step 5: reconstruct best ordering
        order_indices = [0] * m
        mask = size - 1
        pos = m - 1
        while mask:
            j = last_idx[mask]
            if j == -1:
                # Fallback: fill remaining positions with remaining indices
                for idx in range(m - 1, -1, -1):
                    if mask & (1 << idx):
                        order_indices[pos] = idx
                        mask ^= 1 << idx
                        pos -= 1
                break
            order_indices[pos] = j
            mask ^= 1 << j
            pos -= 1

        ordered_cols = [columns[i] for i in order_indices]
        return df_work[ordered_cols]

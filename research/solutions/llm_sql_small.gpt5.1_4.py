import pandas as pd
from typing import List, Any, Tuple


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge: List[List[Any]]) -> pd.DataFrame:
        if not col_merge:
            return df

        df = df.copy()
        original_cols = list(df.columns)

        for group in col_merge:
            if not group:
                continue

            # Map group items (indices/names) to existing column names
            group_cols = []
            for item in group:
                if isinstance(item, int):
                    if 0 <= item < len(original_cols):
                        col_name = original_cols[item]
                        if col_name in df.columns:
                            group_cols.append(col_name)
                else:
                    if item in df.columns:
                        group_cols.append(item)

            # Remove duplicates while preserving order
            seen = set()
            unique_group_cols = []
            for c in group_cols:
                if c not in seen:
                    seen.add(c)
                    unique_group_cols.append(c)

            if len(unique_group_cols) <= 1:
                continue

            # Create merged column name
            new_name = "__MERGED__" + "+".join(map(str, unique_group_cols))

            # Concatenate columns as strings
            base = df[unique_group_cols[0]].astype(str)
            for col in unique_group_cols[1:]:
                base = base + df[col].astype(str)
            df[new_name] = base

            # Drop original columns that were merged
            df.drop(columns=unique_group_cols, inplace=True)

        return df

    def _compute_string_arrays(
        self, df: pd.DataFrame, early_stop: int
    ) -> Tuple[List[str], List[List[str]], List[List[int]]]:
        n_rows = len(df)
        if n_rows == 0:
            return list(df.columns), [], []

        sample_n = min(n_rows, max(1, early_stop))
        sample_df = df.iloc[:sample_n]

        str_arr = sample_df.astype(str).to_numpy()
        _, m_cols = str_arr.shape
        col_names = list(sample_df.columns)

        col_values: List[List[str]] = []
        col_lens: List[List[int]] = []

        for j in range(m_cols):
            vals = list(str_arr[:, j])
            col_values.append(vals)
            col_lens.append([len(v) for v in vals])

        return col_names, col_values, col_lens

    def _distinct_ratios(self, col_values: List[List[str]]) -> List[float]:
        if not col_values:
            return []
        n_rows = len(col_values[0])
        if n_rows == 0:
            return [0.0 for _ in col_values]

        ratios: List[float] = []
        for vals in col_values:
            distinct_cnt = len(set(vals))
            ratios.append(distinct_cnt / float(n_rows))
        return ratios

    def _compute_contribution(
        self, prefix_ids: List[int], values: List[str], lens: List[int]
    ) -> int:
        seen = set()
        contrib = 0
        for i in range(len(values)):
            key = (prefix_ids[i], values[i])
            if key in seen:
                contrib += lens[i]
            else:
                seen.add(key)
        return contrib

    def _update_prefix_ids(
        self, prefix_ids: List[int], values: List[str]
    ) -> List[int]:
        mapping = {}
        new_prefix_ids = [0] * len(prefix_ids)
        next_id = 0
        for i in range(len(values)):
            key = (prefix_ids[i], values[i])
            if key in mapping:
                new_prefix_ids[i] = mapping[key]
            else:
                mapping[key] = next_id
                new_prefix_ids[i] = next_id
                next_id += 1
        return new_prefix_ids

    def _greedy_order(
        self,
        col_values: List[List[str]],
        col_lens: List[List[int]],
        distinct_ratios: List[float],
    ) -> List[int]:
        if not col_values:
            return []

        m_cols = len(col_values)
        n_rows = len(col_values[0])
        prefix_ids = [0] * n_rows

        remaining = set(range(m_cols))
        order: List[int] = []

        while remaining:
            best_col = None
            best_gain = -1
            best_ratio = 2.0  # larger than any possible distinct ratio

            for c in remaining:
                gain = self._compute_contribution(prefix_ids, col_values[c], col_lens[c])
                # Primary: higher gain; Secondary: lower distinct ratio
                if gain > best_gain or (gain == best_gain and distinct_ratios[c] < best_ratio):
                    best_gain = gain
                    best_ratio = distinct_ratios[c]
                    best_col = c

            order.append(best_col)
            prefix_ids = self._update_prefix_ids(prefix_ids, col_values[best_col])
            remaining.remove(best_col)

        return order

    def _eval_order(
        self, order: List[int], col_values: List[List[str]], col_lens: List[List[int]]
    ) -> int:
        if not order:
            return 0
        n_rows = len(col_values[0])
        prefix_ids = [0] * n_rows
        total = 0

        for c in order:
            values = col_values[c]
            lens = col_lens[c]
            seen = set()
            for i in range(n_rows):
                key = (prefix_ids[i], values[i])
                if key in seen:
                    total += lens[i]
                else:
                    seen.add(key)
            prefix_ids = self._update_prefix_ids(prefix_ids, values)

        return total

    def _local_optimize(
        self,
        initial_order: List[int],
        col_values: List[List[str]],
        col_lens: List[List[int]],
        max_iters: int = 1,
    ) -> List[int]:
        if not initial_order:
            return initial_order

        best_order = list(initial_order)
        best_score = self._eval_order(best_order, col_values, col_lens)

        m_cols = len(best_order)
        if m_cols <= 2:
            return best_order

        for _ in range(max_iters):
            improved = False
            for i in range(m_cols - 1):
                for j in range(i + 1, m_cols):
                    candidate = list(best_order)
                    candidate[i], candidate[j] = candidate[j], candidate[i]
                    score = self._eval_order(candidate, col_values, col_lens)
                    if score > best_score:
                        best_score = score
                        best_order = candidate
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break

        return best_order

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
        # Apply column merges if specified
        df_work = df
        if col_merge:
            df_work = self._apply_col_merge(df_work, col_merge)

        # If there are 0 or 1 columns after merge, nothing to reorder
        if df_work.shape[1] <= 1:
            return df_work

        # Build string representations and lengths (possibly on a row sample)
        col_names, col_values, col_lens = self._compute_string_arrays(df_work, early_stop)

        # Compute distinct ratios for heuristic tie-breaking
        distinct_ratios = self._distinct_ratios(col_values)

        # Greedy construction of column order
        initial_order = self._greedy_order(col_values, col_lens, distinct_ratios)

        # Local search (2-opt style) to refine order; limit iterations for speed
        optimized_order = self._local_optimize(initial_order, col_values, col_lens, max_iters=1)

        # Reorder columns of the full DataFrame (not just the sampled rows)
        final_col_order = [col_names[i] for i in optimized_order]
        return df_work[final_col_order].copy()
import pandas as pd
from collections import defaultdict


class Solution:
    def _apply_column_merges(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        orig_cols = list(df.columns)
        col_to_group = {}
        groups = []

        # Resolve groups to original column names
        for group in col_merge:
            if not group:
                continue
            names = []
            for item in group:
                if isinstance(item, int):
                    if 0 <= item < len(orig_cols):
                        names.append(orig_cols[item])
                else:
                    if item in orig_cols:
                        names.append(item)
            # Deduplicate while preserving order
            seen = set()
            unique_names = []
            for name in names:
                if name not in seen:
                    seen.add(name)
                    unique_names.append(name)
            if len(unique_names) >= 2:
                g = tuple(unique_names)
                groups.append(g)
                for c in unique_names:
                    col_to_group[c] = g

        if not groups:
            return df

        # Precompute merged series for each group
        group_to_series = {}
        for g in groups:
            if g in group_to_series:
                continue
            merged_series = df.loc[:, list(g)].astype(str).agg(''.join, axis=1)
            group_to_series[g] = merged_series

        # Build new DataFrame columns order and data
        new_cols = []
        new_data = {}
        seen_groups = set()

        for c in orig_cols:
            g = col_to_group.get(c)
            if not g:
                new_cols.append(c)
                new_data[c] = df[c]
            else:
                if g in seen_groups:
                    continue
                seen_groups.add(g)
                # Use first column name as base name, avoid collisions
                new_name = g[0]
                if new_name in new_data:
                    base = new_name
                    suffix = 1
                    while f"{base}_m{suffix}" in new_data:
                        suffix += 1
                    new_name = f"{base}_m{suffix}"
                new_cols.append(new_name)
                new_data[new_name] = group_to_series[g]

        new_df = pd.DataFrame(new_data, columns=new_cols, index=df.index)
        return new_df

    def _prepare_column_stats(self, df: pd.DataFrame):
        col_names = list(df.columns)
        n_rows = len(df)
        n_cols = len(col_names)

        col_ids = [None] * n_cols
        col_lengths = [None] * n_cols
        distinct_ratios = [0.0] * n_cols
        avg_lengths = [0.0] * n_cols
        top_freq_ratios = [0.0] * n_cols

        for col_idx, col_name in enumerate(col_names):
            arr = df[col_name].to_numpy()
            # Ensure string representation for all values
            str_arr = arr.astype(str)

            n_local = len(str_arr)
            ids = [0] * n_local
            lengths = [0] * n_local
            value_to_id = {}
            freq = defaultdict(int)
            next_id = 0

            for i in range(n_local):
                s = str_arr[i]
                lengths[i] = len(s)
                v_id = value_to_id.get(s)
                if v_id is None:
                    v_id = next_id
                    value_to_id[s] = v_id
                    next_id += 1
                freq[v_id] += 1
                ids[i] = v_id

            col_ids[col_idx] = ids
            col_lengths[col_idx] = lengths

            if n_local > 0:
                distinct_count = next_id
                distinct_ratios[col_idx] = distinct_count / float(n_local)
                avg_lengths[col_idx] = sum(lengths) / float(n_local)
                max_freq = max(freq.values()) if freq else 0
                top_freq_ratios[col_idx] = max_freq / float(n_local)
            else:
                distinct_ratios[col_idx] = 0.0
                avg_lengths[col_idx] = 0.0
                top_freq_ratios[col_idx] = 0.0

        return col_ids, col_lengths, distinct_ratros, avg_lengths, top_freq_ratios, col_names

    def _approximate_score(self, order, col_ids, col_lengths, n_rows, row_limit):
        limit = n_rows if row_limit is None else min(n_rows, row_limit)
        root = {}
        total_lcp = 0

        for i in range(limit):
            node = root
            char_sum = 0
            for col_idx in order:
                vid = col_ids[col_idx][i]
                child = node.get(vid)
                if child is None:
                    break
                node = child
                char_sum += col_lengths[col_idx][i]
            total_lcp += char_sum

            # Insert current row's prefix path
            node = root
            for col_idx in order:
                vid = col_ids[col_idx][i]
                child = node.get(vid)
                if child is None:
                    child = {}
                    node[vid] = child
                node = child

        return total_lcp

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
        """
        Reorder columns in the DataFrame to maximize prefix hit rate.
        """
        if df is None or df.empty:
            return df.copy()

        # Apply column merges if specified
        df_work = self._apply_column_merges(df, col_merge) if col_merge else df

        n_rows = len(df_work)
        if n_rows <= 1:
            return df_work.copy()

        (
            col_ids,
            col_lengths,
            distinct_ratios,
            avg_lengths,
            top_freq_ratios,
            col_names,
        ) = self._prepare_column_stats(df_work)

        n_cols = len(col_names)
        if n_cols <= 1:
            return df_work.copy()

        indices = list(range(n_cols))

        # Partition columns by distinct value ratio
        low_card = []
        high_card = []
        for i in indices:
            if distinct_ratios[i] < distinct_value_threshold:
                low_card.append(i)
            else:
                high_card.append(i)

        # Heuristic scoring for initial ordering
        def low_key(i):
            # Higher potential earlier: low distinct ratio, high avg length, high top frequency
            return -(1.0 - distinct_ratios[i]) * (avg_lengths[i] + 1e-6) * (top_freq_ratios[i] + 1e-6)

        def high_key(i):
            # Among high-card columns, prefer smaller distinct ratio and shorter avg length
            return (distinct_ratios[i], avg_lengths[i])

        low_card.sort(key=low_key)
        high_card.sort(key=high_key)
        order = low_card + high_card

        # Normalize early_stop
        if early_stop is None or early_stop <= 0:
            early_stop = n_rows

        # Determine sample size for approximate scoring
        base_sample = min(n_rows, early_stop, 10000)
        if row_stop is not None and row_stop > 0:
            computed = row_stop * 2500
            if computed < 1000:
                computed = 1000
            sample_rows = min(n_rows, early_stop, max(base_sample, computed))
        else:
            sample_rows = base_sample

        best_score = self._approximate_score(order, col_ids, col_lengths, n_rows, sample_rows)

        # Local search with pairwise swaps
        max_iters = 5
        iter_count = 0
        improved = True

        while improved and iter_count < max_iters:
            improved = False
            iter_count += 1
            for a in range(n_cols):
                for b in range(a + 1, n_cols):
                    if order[a] == order[b]:
                        continue
                    candidate = list(order)
                    candidate[a], candidate[b] = candidate[b], candidate[a]
                    score = self._approximate_score(candidate, col_ids, col_lengths, n_rows, sample_rows)
                    if score > best_score:
                        best_score = score
                        order = candidate
                        improved = True
                        break
                if improved:
                    break

        final_cols = [col_names[i] for i in order]
        result_df = df_work.loc[:, final_cols]
        return result_df

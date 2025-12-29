import pandas as pd


class Solution:
    def _apply_col_merges(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df
        # Work on a copy to avoid mutating the original DataFrame
        df_out = df.copy()
        for group in col_merge:
            if not group:
                continue
            # Only consider columns that actually exist in df_out
            existing = [col for col in group if col in df_out.columns]
            if len(existing) <= 1:
                # Nothing to merge or only one column present
                continue
            # Create a deterministic merged column name
            new_col_name = "|".join(existing)
            # Concatenate as strings row-wise
            df_out[new_col_name] = df_out[existing].astype(str).agg("".join, axis=1)
            # Drop the original columns
            df_out.drop(columns=existing, inplace=True)
        return df_out

    def _compute_hit_rate(self, order, col_arrays, total_chars):
        if total_chars <= 0 or not order:
            return 0.0

        # Prepare arrays in the order of columns to avoid repeated dict lookups
        arr_list = [col_arrays[c] for c in order]
        if not arr_list:
            return 0.0

        n_rows = len(arr_list[0])
        if n_rows == 0:
            return 0.0

        root = {}
        lcp_sum = 0

        for i in range(n_rows):
            node = root
            matched = True
            lcp_len = 0

            for arr in arr_list:
                val = arr[i]
                # val is ensured to be a string
                for ch in val:
                    if matched:
                        child = node.get(ch)
                        if child is not None:
                            node = child
                            lcp_len += 1
                        else:
                            matched = False
                            new_node = {}
                            node[ch] = new_node
                            node = new_node
                    else:
                        child = node.get(ch)
                        if child is None:
                            child = {}
                            node[ch] = child
                        node = child

            lcp_sum += lcp_len

        return lcp_sum / total_chars

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
        # Apply column merges if specified and possible
        df_proc = self._apply_col_merges(df, col_merge)

        cols = list(df_proc.columns)
        n_cols = len(cols)
        n_rows = len(df_proc)

        if n_cols <= 1 or n_rows == 0:
            # Nothing to reorder
            return df_proc

        # Convert to string DataFrame for analysis and string concatenation
        df_str = df_proc.astype(str)

        # Precompute per-column string arrays and metrics
        col_arrays = {}
        metrics = {}  # col -> (distinct_ratio, avg_len, mode_freq)
        total_chars = 0

        for col in cols:
            arr = df_str[col].to_numpy(copy=False)
            col_arrays[col] = arr

            value_counts = {}
            total_len_col = 0

            for v in arr:
                # v is already a string
                total_len_col += len(v)
                value_counts[v] = value_counts.get(v, 0) + 1

            n_unique = len(value_counts)
            maxfreq = max(value_counts.values()) if value_counts else 0

            if n_rows > 0:
                distinct_ratio = n_unique / n_rows
                avg_len = total_len_col / n_rows
                mode_freq = maxfreq / n_rows
            else:
                distinct_ratio = 0.0
                avg_len = 0.0
                mode_freq = 0.0

            metrics[col] = (distinct_ratio, avg_len, mode_freq)
            total_chars += total_len_col

        if total_chars <= 0:
            # All empty strings; ordering does not matter
            return df_proc

        # Build candidate column orders
        candidate_orders = []
        seen_orders = set()

        def add_order(order):
            key = tuple(order)
            if key not in seen_orders:
                seen_orders.add(key)
                candidate_orders.append(order)

        # Baseline: original order
        add_order(cols)

        # Heuristic orders based on simple column statistics
        def distinct_asc_order():
            return sorted(
                cols,
                key=lambda c: (
                    metrics[c][0],      # distinct_ratio ascending
                    -metrics[c][1],     # avg_len descending
                    -metrics[c][2],     # mode_freq descending
                ),
            )

        def length_desc_order():
            return sorted(
                cols,
                key=lambda c: (
                    -metrics[c][1],     # avg_len descending
                    metrics[c][0],      # distinct_ratio ascending
                    -metrics[c][2],     # mode_freq descending
                ),
            )

        def modefreq_desc_order():
            return sorted(
                cols,
                key=lambda c: (
                    -metrics[c][2],     # mode_freq descending
                    metrics[c][0],      # distinct_ratio ascending
                    -metrics[c][1],     # avg_len descending
                ),
            )

        def combined_score_order():
            # Sort by an approximate "noise" score: smaller is better
            # score ~ distinct_ratio / (avg_len * mode_freq)
            def score(c):
                dr, al, mf = metrics[c]
                denom = al * mf
                if denom <= 0:
                    return float("inf")
                return dr / denom

            return sorted(cols, key=score)

        heuristic_generators = [
            distinct_asc_order,
            length_desc_order,
            modefreq_desc_order,
            combined_score_order,
        ]

        max_extra = max(0, int(col_stop))
        for gen in heuristic_generators:
            if len(candidate_orders) >= 1 + max_extra:
                break
            order = gen()
            add_order(order)

        # Evaluate all candidate orders and choose the best by true hit rate
        best_order = candidate_orders[0]
        best_hit_rate = self._compute_hit_rate(best_order, col_arrays, total_chars)

        for order in candidate_orders[1:]:
            hr = self._compute_hit_rate(order, col_arrays, total_chars)
            if hr > best_hit_rate:
                best_hit_rate = hr
                best_order = order

        # Return DataFrame with columns reordered according to the best order found
        return df_proc[best_order]
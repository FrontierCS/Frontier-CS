import pandas as pd


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df = df.copy()
        for group in col_merge:
            if not group:
                continue

            # Resolve group items to column names that currently exist in df
            names = []
            for item in group:
                if isinstance(item, int):
                    # Treat as column index
                    if 0 <= item < len(df.columns):
                        names.append(df.columns[item])
                else:
                    # Treat as column name
                    if item in df.columns:
                        names.append(item)

            # Remove duplicates while preserving order
            if not names:
                continue
            names = list(dict.fromkeys(names))

            # Ensure at least two distinct columns and all still exist
            if len(names) <= 1:
                continue
            if not all(name in df.columns for name in names):
                continue

            # Determine insertion position (position of first column in group)
            first_idx = min(df.columns.get_loc(name) for name in names)

            # Create a unique merged column name
            base_name = "_MERGED_".join(map(str, names))
            new_name = base_name
            suffix = 1
            while new_name in df.columns:
                suffix += 1
                new_name = f"{base_name}_{suffix}"

            # Concatenate string representations of the group columns
            merged_series = df[names].astype(str).agg("".join, axis=1)

            # Drop original columns and insert merged column
            df = df.drop(columns=names)
            df.insert(first_idx, new_name, merged_series)

        return df

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
        # Work on a copy to avoid mutating the input DataFrame
        if col_merge:
            df_work = self._apply_col_merge(df, col_merge)
        else:
            df_work = df.copy()

        n_rows = len(df_work)
        if n_rows == 0:
            return df_work

        col_names = list(df_work.columns)
        m_cols = len(col_names)
        if m_cols <= 1:
            return df_work

        # Determine number of rows to sample for optimization
        if early_stop is not None and early_stop > 0:
            sample_n = min(n_rows, int(early_stop))
        else:
            sample_n = n_rows

        if sample_n < 2:
            # Not enough rows to estimate prefix sharing; return as is
            return df_work

        # Use first sample_n rows for statistics
        df_sample = df_work.iloc[:sample_n]

        # Precompute per-column string data, average lengths, distinct ratios, and pair counts
        data_cols = []          # list of list-of-str per column
        weights = []            # average string length per column
        P1 = []                 # sum_{values} C(count, 2) for single column
        distinct_ratio = []     # distinct values / sample_n

        for col in col_names:
            series_str = df_sample[col].astype(str)
            col_list = series_str.tolist()
            data_cols.append(col_list)

            # Average string length
            total_len = 0
            for s in col_list:
                total_len += len(s)
            avg_len = total_len / sample_n if sample_n > 0 else 0.0
            weights.append(avg_len)

            # Value counts for distinct ratio and P1
            counts = {}
            for v in col_list:
                counts[v] = counts.get(v, 0) + 1

            p1 = 0
            for cnt in counts.values():
                if cnt > 1:
                    p1 += cnt * (cnt - 1) // 2
            P1.append(p1)
            distinct_ratio.append(len(counts) / sample_n)

        indices = list(range(m_cols))

        # Base score: average length * pair count for equality in that column
        base_score = [weights[i] * P1[i] for i in indices]

        # Base orderings: by descending base_score, and by distinct ratio
        order_score_desc = sorted(
            indices,
            key=lambda j: (-base_score[j], weights[j], j),
        )

        order_distinct = sorted(
            indices,
            key=lambda j: (
                distinct_ratio[j] >= distinct_value_threshold,
                distinct_ratio[j],
                -weights[j],
                j,
            ),
        )

        original_order = list(range(m_cols))

        # Evaluation function for a permutation using the pair-based surrogate objective
        def evaluate_perm(perm):
            n = sample_n
            pre_keys = [None] * n
            total = 0.0
            data_cols_local = data_cols
            weights_local = weights

            for col_idx in perm:
                col_data = data_cols_local[col_idx]
                mapping = {}
                get_mapping = mapping.get

                # Build groups for current prefix
                for i in range(n):
                    prev_key = pre_keys[i]
                    v = col_data[i]
                    if prev_key is None:
                        key = v
                    else:
                        key = (prev_key, v)
                    pre_keys[i] = key

                    cnt = get_mapping(key)
                    if cnt is None:
                        mapping[key] = 1
                    else:
                        mapping[key] = cnt + 1

                # Compute number of equal-prefix pairs at this depth
                pairs = 0
                for cnt in mapping.values():
                    if cnt > 1:
                        pairs += cnt * (cnt - 1) // 2

                total += weights_local[col_idx] * pairs

            return total

        # Search for a good permutation
        max_evals = 200  # hard cap on the number of full evaluations

        best_perm = None
        best_score = None
        eval_count = 0
        visited = set()

        def eval_and_update(perm):
            nonlocal best_perm, best_score, eval_count
            t = tuple(perm)
            if t in visited:
                return
            visited.add(t)
            score = evaluate_perm(perm)
            eval_count += 1
            if best_score is None or score > best_score:
                best_score = score
                best_perm = perm

        # Evaluate baseline permutations
        eval_and_update(original_order)
        eval_and_update(order_score_desc)
        eval_and_update(list(reversed(order_score_desc)))
        eval_and_update(order_distinct)
        eval_and_update(list(reversed(order_distinct)))

        # Greedy construction guided by full-evaluation surrogate
        def greedy_build(reverse_tail=False):
            nonlocal best_perm, best_score, eval_count
            prefix = []
            remaining = list(range(m_cols))

            while remaining and eval_count < max_evals:
                best_local_c = None
                best_local_score = None

                for c in remaining:
                    # Tail order for remaining columns (after choosing c next)
                    tail = [x for x in remaining if x != c]
                    if tail:
                        if not reverse_tail:
                            tail_sorted = sorted(
                                tail,
                                key=lambda j: (-base_score[j], weights[j], j),
                            )
                        else:
                            tail_sorted = sorted(
                                tail,
                                key=lambda j: (base_score[j], -weights[j], j),
                            )
                    else:
                        tail_sorted = []

                    perm = prefix + [c] + tail_sorted
                    t_perm = tuple(perm)
                    if t_perm in visited:
                        continue

                    score = evaluate_perm(perm)
                    visited.add(t_perm)
                    eval_count += 1

                    if best_score is None or score > best_score:
                        best_score = score
                        best_perm = perm

                    if best_local_score is None or score > best_local_score:
                        best_local_score = score
                        best_local_c = c

                    if eval_count >= max_evals:
                        break

                if best_local_c is None:
                    # No new permutations evaluated (all visited or eval cap reached)
                    break

                prefix.append(best_local_c)
                remaining.remove(best_local_c)

        greedy_build(False)
        if eval_count < max_evals:
            greedy_build(True)

        # Fallback in case something went wrong
        if best_perm is None:
            best_perm = order_score_desc

        # Reorder columns of the working DataFrame according to best_perm
        reordered_cols = [col_names[i] for i in best_perm]
        df_out = df_work[reordered_cols]

        return df_out
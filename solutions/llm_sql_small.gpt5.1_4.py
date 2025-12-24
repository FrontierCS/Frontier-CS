import pandas as pd
from typing import List, Any, Dict


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge: List[List[Any]]) -> pd.DataFrame:
        """
        Apply column merges as specified in col_merge.
        Each group of columns is concatenated (as strings, no separator) into a new column.
        Original columns in the group are removed.
        If group columns are not present, the group is skipped (assumes merges may be pre-applied).
        """
        if not col_merge:
            return df

        df_work = df.copy()
        used_cols = set()

        for group in col_merge:
            if not group:
                continue
            # Keep only columns that currently exist and are not already merged
            group_list = [c for c in group if c in df_work.columns and c not in used_cols]
            if len(group_list) <= 1:
                # Nothing to merge or already merged
                continue

            # Generate a new unique column name
            base_new_name = "MERGED_" + "_".join(map(str, group_list))
            new_name = base_new_name
            suffix = 1
            while new_name in df_work.columns:
                new_name = f"{base_new_name}__{suffix}"
                suffix += 1

            # Concatenate as strings without separators
            df_work[new_name] = df_work[group_list].astype(str).agg(''.join, axis=1)

            # Mark original columns for removal
            for c in group_list:
                used_cols.add(c)

        if used_cols:
            df_work = df_work.drop(columns=list(used_cols))

        return df_work

    @staticmethod
    def _evaluate_order(str_cols: Dict[Any, List[str]], columns_order: List[Any]) -> float:
        """
        Approximate objective for a given column order.
        Uses lexicographic sorting and neighbor LCP as proxy for max LCP across all rows.
        """
        if not columns_order:
            return 0.0

        # Build row strings by concatenating column strings in the specified order
        arrays = [str_cols[col] for col in columns_order]
        if not arrays:
            return 0.0

        # zip(*) to get rows; each row_vals is a tuple/list of column strings for that row
        strings = ["".join(row_vals) for row_vals in zip(*arrays)]
        n = len(strings)
        if n <= 1:
            return 0.0

        # Precompute lengths and total length (denominator)
        lengths = [0] * n
        total_len = 0
        for i, s in enumerate(strings):
            l = len(s)
            lengths[i] = l
            total_len += l

        if total_len == 0:
            return 0.0

        strings_get = strings.__getitem__

        # Sort indices lexicographically by string; neighbor LCP approximates global best LCP
        indices = list(range(n))
        indices.sort(key=strings_get)

        total_lcp = 0
        for pos in range(n):
            idx = indices[pos]
            s = strings_get(idx)
            best = 0

            # Compare with previous neighbor
            if pos > 0:
                idx_prev = indices[pos - 1]
                s_prev = strings_get(idx_prev)
                len1 = lengths[idx]
                len2 = lengths[idx_prev]
                limit = len1 if len1 < len2 else len2
                i2 = 0
                while i2 < limit and s[i2] == s_prev[i2]:
                    i2 += 1
                best = i2

            # Compare with next neighbor
            if pos + 1 < n:
                idx_next = indices[pos + 1]
                s_next = strings_get(idx_next)
                len1 = lengths[idx]
                len2 = lengths[idx_next]
                limit = len1 if len1 < len2 else len2
                i2 = 0
                while i2 < limit and s[i2] == s_next[i2]:
                    i2 += 1
                if i2 > best:
                    best = i2

            total_lcp += best

        return total_lcp / float(total_len)

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
        # Step 1: Apply column merges if necessary
        df_work = df.copy()
        df_work = self._apply_col_merge(df_work, col_merge)

        columns = list(df_work.columns)
        num_cols = len(columns)
        n_rows = len(df_work)

        if num_cols <= 1 or n_rows == 0:
            return df_work

        # Step 2: Choose sample size for approximate evaluation
        # Cap sample size to remain within runtime constraints
        max_sample_n = 5000

        # Use row_stop as multiplier for 1000 rows if provided
        try:
            if row_stop is not None:
                rs = int(row_stop)
                if rs > 0:
                    candidate = rs * 1000
                    if candidate < max_sample_n:
                        max_sample_n = candidate
        except Exception:
            pass

        # Use early_stop as an upper bound on rows if it's smaller
        try:
            if early_stop is not None:
                es = int(early_stop)
                if es > 0 and es < max_sample_n:
                    max_sample_n = es
        except Exception:
            pass

        if max_sample_n <= 0:
            max_sample_n = min(n_rows, 1000)

        sample_n = min(n_rows, max_sample_n)
        sample_df = df_work.iloc[:sample_n]

        # Step 3: Compute basic statistics per column on sample rows
        str_cols: Dict[Any, List[str]] = {}
        col_scores: Dict[Any, Any] = {}

        for col in columns:
            series = sample_df[col]
            series_str = series.astype(str)
            values_list = series_str.tolist()
            str_cols[col] = values_list

            # Average string length
            lengths = series_str.str.len()
            avg_len = float(lengths.mean()) if sample_n > 0 else 0.0

            # Distinct ratio based on string representation
            nunique = int(series_str.nunique(dropna=False)) if sample_n > 0 else 0
            distinct_ratio = float(nunique) / float(sample_n) if sample_n > 0 else 1.0

            # Heuristic: columns with low distinct ratio and long strings are preferred earlier
            base_score = (1.0 - distinct_ratio) * avg_len

            # Slightly penalize very high-cardinality columns beyond the base score
            if distinct_ratio > distinct_value_threshold:
                base_score *= 0.5

            col_scores[col] = (base_score, distinct_ratio, avg_len)

        # Step 4: Initial order: sort by heuristic score (descending)
        base_order = sorted(
            columns,
            key=lambda c: (
                -col_scores[c][0],   # higher base_score first
                col_scores[c][1],    # lower distinct_ratio first
                -col_scores[c][2],   # longer avg_len first
                str(c),
            ),
        )

        # Step 5: Local search (pairwise swap hill-climbing) with approximate evaluation
        # Limit the number of evaluations to keep within time budget
        try:
            es = int(early_stop) if early_stop is not None else 100000
        except Exception:
            es = 100000
        if es <= 0:
            es = 1
        max_evals = min(es, 250)  # hard cap

        best_order = list(base_order)
        best_score = self._evaluate_order(str_cols, best_order)
        eval_count = 1

        if num_cols > 1 and sample_n > 1 and max_evals > 1:
            improved = True
            while improved and eval_count < max_evals:
                improved = False
                # Explore all pairwise swaps; restart search when an improvement is found
                for i in range(num_cols):
                    if improved or eval_count >= max_evals:
                        break
                    for j in range(i + 1, num_cols):
                        if eval_count >= max_evals:
                            break
                        # Swap columns i and j
                        new_order = best_order.copy()
                        new_order[i], new_order[j] = new_order[j], new_order[i]
                        score = self._evaluate_order(str_cols, new_order)
                        eval_count += 1
                        if score > best_score + 1e-9:
                            best_score = score
                            best_order = new_order
                            improved = True
                            break

        # Step 6: Reorder columns in the full DataFrame according to best_order
        return df_work[best_order]

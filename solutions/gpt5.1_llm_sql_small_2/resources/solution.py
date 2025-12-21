import pandas as pd
from typing import List, Any


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
        # Step 1: Apply column merges (on a copy of df)
        df_work = df.copy()

        if col_merge:
            orig_cols = list(df_work.columns)

            # Resolve merge groups to column names
            merge_groups: List[List[str]] = []
            for group in col_merge:
                names: List[str] = []
                for spec in group:
                    if isinstance(spec, int):
                        idx = spec if spec >= 0 else len(orig_cols) + spec
                        if 0 <= idx < len(orig_cols):
                            col_name = orig_cols[idx]
                        else:
                            continue
                    else:
                        col_name = str(spec)
                    if col_name in df_work.columns:
                        names.append(col_name)
                # Deduplicate while preserving order
                seen = set()
                unique_names: List[str] = []
                for n in names:
                    if n not in seen:
                        seen.add(n)
                        unique_names.append(n)
                if len(unique_names) > 1:
                    merge_groups.append(unique_names)

            # Apply merges sequentially
            for names in merge_groups:
                existing = [n for n in names if n in df_work.columns]
                if len(existing) <= 1:
                    continue
                target_name = existing[0]
                # Build merged string column from the existing columns
                merged_series = df_work[existing].astype(str).agg("".join, axis=1)
                # Drop original columns in the group
                df_work = df_work.drop(columns=existing)
                # Add merged column (reusing the first column's name)
                df_work[target_name] = merged_series

        # After merges, determine column order to optimize
        cols = list(df_work.columns)
        M = len(cols)
        N_total = len(df_work)

        # If there's nothing to optimize, just return the possibly-merged df
        if M <= 1 or N_total <= 1:
            return df_work

        # Step 2: Prepare data for scoring
        # Limit number of rows used for optimization to early_stop
        if early_stop is not None and early_stop > 0:
            N_sample = min(N_total, early_stop)
        else:
            N_sample = N_total

        if N_sample < 2:
            # Not enough rows for any prefix reuse analysis
            return df_work

        # Extract string representations per column for sampled rows
        col_values_str: List[List[str]] = []
        col_lens: List[List[int]] = []

        for col in cols:
            values = df_work[col].iloc[:N_sample].tolist()
            str_vals = [str(v) for v in values]
            lens = [len(s) for s in str_vals]
            col_values_str.append(str_vals)
            col_lens.append(lens)

        N_pairs = N_sample - 1

        # Precompute LCP length and full-equality flags for consecutive rows, per column
        lcp_cols: List[List[int]] = []
        eq_cols: List[List[bool]] = []

        for c in range(M):
            vals = col_values_str[c]
            lens = col_lens[c]
            lcp_list = [0] * N_pairs
            eq_list = [False] * N_pairs

            for i in range(1, N_sample):
                s1 = vals[i - 1]
                s2 = vals[i]
                len1 = lens[i - 1]
                len2 = lens[i]
                limit = len1 if len1 < len2 else len2
                k = 0
                # Compute LCP length
                while k < limit and s1[k] == s2[k]:
                    k += 1
                lcp_list[i - 1] = k
                eq_list[i - 1] = (k == len1 and k == len2)

            lcp_cols.append(lcp_list)
            eq_cols.append(eq_list)

        # Step 3: Heuristic scores per column (distinctness and average length)
        distinct_ratios: List[float] = []
        avg_lens: List[float] = []
        scores: List[float] = []

        for idx, col in enumerate(cols):
            series = df_work[col]
            n_unique = float(series.nunique(dropna=False))
            ratio = n_unique / float(N_total) if N_total > 0 else 0.0
            distinct_ratios.append(ratio)

            lens_sample = col_lens[idx]
            if lens_sample:
                avg_len = float(sum(lens_sample)) / float(len(lens_sample))
            else:
                avg_len = 0.0
            avg_lens.append(avg_len)

            score = ratio * avg_len
            if ratio > distinct_value_threshold:
                score *= 2.0
            scores.append(score)

        # Sort column indices by heuristic score (low first => more stable, shorter first)
        sorted_indices = sorted(range(M), key=lambda i: scores[i])

        # Step 4: Define scoring function for a permutation (approximate objective)
        def score_perm(perm: List[int]) -> int:
            perm_len = len(perm)
            if perm_len == 0:
                return 0
            # Pre-resolve column-wise arrays for this permutation
            lcp_seq = [lcp_cols[c] for c in perm]
            eq_seq = [eq_cols[c] for c in perm]
            total_score = 0
            for pair_idx in range(N_pairs):
                acc = 0
                for k in range(perm_len):
                    l = lcp_seq[k][pair_idx]
                    acc += l
                    if not eq_seq[k][pair_idx]:
                        break
                total_score += acc
            return total_score

        # Step 5: Greedy insertion search with multiple seeds
        best_global_score = -1
        best_global_perm: List[int] = list(range(M))  # fallback

        for seed in sorted_indices:
            order: List[int] = [seed]
            current_score: Any = None

            remaining = [idx for idx in sorted_indices if idx != seed]

            for col_idx in remaining:
                best_local_score = -1
                best_local_order: List[int] = []

                # Try inserting col_idx at every position in current order
                for pos in range(len(order) + 1):
                    candidate = order[:pos] + [col_idx] + order[pos:]
                    sc = score_perm(candidate)
                    if sc > best_local_score:
                        best_local_score = sc
                        best_local_order = candidate

                order = best_local_order
                current_score = best_local_score

            if current_score is None:
                # Only one column in this seed case
                current_score = score_perm(order)

            if current_score > best_global_score:
                best_global_score = current_score
                best_global_perm = order

        # Step 6: Reorder df_work columns according to best permutation
        final_cols_order = [cols[idx] for idx in best_global_perm]
        result_df = df_work[final_cols_order]

        return result_df

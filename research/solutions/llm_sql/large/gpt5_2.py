import pandas as pd
import numpy as np
import time
from typing import List, Tuple


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
        start_time = time.time()
        time_limit = 9.5

        def apply_col_merge(df_in: pd.DataFrame, merges: list) -> pd.DataFrame:
            if not merges:
                return df_in
            df_local = df_in.copy()
            used_cols = set()
            new_columns = []
            to_drop = []
            for idx, group in enumerate(merges):
                present = [c for c in group if c in df_local.columns and c not in used_cols]
                if len(present) <= 1:
                    continue
                # Build merged string array efficiently
                arr_merged = None
                for k, col in enumerate(present):
                    arr = df_local[col].astype(str).to_numpy(copy=False)
                    if arr_merged is None:
                        arr_merged = arr.copy()
                    else:
                        arr_merged = np.char.add(arr_merged, arr)
                new_col_name = "MERGED__" + "__".join(present)
                # Ensure unique name if collision
                base_name = new_col_name
                suffix = 1
                while new_col_name in df_local.columns:
                    new_col_name = f"{base_name}__{suffix}"
                    suffix += 1
                df_local[new_col_name] = pd.Series(arr_merged, index=df_local.index)
                to_drop.extend(present)
                used_cols.update(present)
                new_columns.append(new_col_name)
            if to_drop:
                # Keep new merged columns after dropping the originals
                keep_cols = [c for c in df_local.columns if c not in to_drop]
                df_local = df_local[keep_cols]
            return df_local

        def precompute_column_data(df_in: pd.DataFrame):
            # Returns column names, codes list, lengths list, global contributions, unique ratios, avg lengths
            col_names = list(df_in.columns)
            n_rows = len(df_in)
            codes_list = []
            lens_list = []
            global_contribs = []
            unique_ratios = []
            avg_lens = []
            # Pre-cast all columns to strings once for speed
            # But to save memory, we do per column
            for col in col_names:
                vals_str = df_in[col].astype(str).to_numpy(copy=False)
                lens = np.char.str_len(vals_str).astype(np.int32)
                codes, uniques = pd.factorize(vals_str, sort=False)
                counts = np.bincount(codes)
                sumlen = np.bincount(codes, weights=lens.astype(np.float64))
                # Avoid division by zero
                with np.errstate(divide='ignore', invalid='ignore'):
                    contrib = (sumlen * (1.0 - (1.0 / np.maximum(counts, 1)))).sum()
                codes_list.append(codes.astype(np.int32))
                lens_list.append(lens.astype(np.int32))
                global_contribs.append(float(contrib))
                unique_ratios.append(min(len(uniques), n_rows) / float(n_rows) if n_rows > 0 else 1.0)
                avg_lens.append(float(lens.mean() if n_rows > 0 else 0.0))
            return col_names, codes_list, lens_list, np.array(global_contribs, dtype=np.float64), np.array(unique_ratios, dtype=np.float64), np.array(avg_lens, dtype=np.float64)

        def compute_pair_contrib(group_codes: np.ndarray, col_codes: np.ndarray, lens: np.ndarray) -> float:
            # group_codes: current group IDs (int), col_codes: codes of candidate column, lens: lengths of candidate column
            # Contribution equals sum over unique pairs (g, v): sum_len * (1 - 1/count)
            A = np.empty((group_codes.shape[0], 2), dtype=np.int64)
            A[:, 0] = group_codes
            A[:, 1] = col_codes
            _, inv, counts = np.unique(A, axis=0, return_inverse=True, return_counts=True)
            sum_len = np.bincount(inv, weights=lens.astype(np.float64), minlength=counts.shape[0])
            with np.errstate(divide='ignore', invalid='ignore'):
                contrib = (sum_len * (1.0 - (1.0 / np.maximum(counts, 1)))).sum()
            return float(contrib)

        def update_groups(group_codes: np.ndarray, col_codes: np.ndarray) -> np.ndarray:
            A = np.empty((group_codes.shape[0], 2), dtype=np.int64)
            A[:, 0] = group_codes
            A[:, 1] = col_codes
            _, inv = np.unique(A, axis=0, return_inverse=True)
            return inv.astype(np.int32)

        # Step 1: Apply merges
        df_work = apply_col_merge(df, col_merge)

        # Step 2: Precompute stats per column
        col_names, codes_list, lens_list, global_contribs, uniq_ratios, avg_lens = precompute_column_data(df_work)
        n_rows = len(df_work)
        m_cols = len(col_names)

        if m_cols == 0:
            return df_work

        # Initial ranking by global contributions (descending), with slight boost for lower unique ratios and longer avg length
        # Weighted score: primary global contribution, secondary duplication rate * avg length
        duplication_rate = 1.0 - uniq_ratios
        secondary = duplication_rate * np.maximum(avg_lens, 1e-6)
        init_score = global_contribs + 0.1 * secondary * n_rows
        remaining_idx = list(np.argsort(-init_score))

        # Greedy selection with group-aware incremental contribution for a candidate pool
        selected_idx: List[int] = []
        group_codes = np.zeros(n_rows, dtype=np.int32)

        # Candidate pool size depends on col_stop; allow more candidates but keep bounded
        pool_size = max(8, min(24, int(8 * max(1, col_stop))))
        # For very wide tables, increase pool a bit
        if m_cols > 40:
            pool_size = min(32, max(pool_size, 16))

        # Perform full greedy until time limit or all columns selected
        # For speed, we may reduce to naive order after many steps
        steps_done = 0
        while remaining_idx and (time.time() - start_time) < time_limit:
            # Candidate pool
            pool = remaining_idx[:min(pool_size, len(remaining_idx))]
            best_c = None
            best_contrib = -1.0

            # Evaluate contributions for candidates in pool
            for idx in pool:
                contrib = compute_pair_contrib(group_codes, codes_list[idx], lens_list[idx])
                if contrib > best_contrib:
                    best_contrib = contrib
                    best_c = idx
            if best_c is None:
                break

            # Select best and update
            selected_idx.append(best_c)
            group_codes = update_groups(group_codes, codes_list[best_c])
            remaining_idx.remove(best_c)
            steps_done += 1

            # If time is tight, break
            if (time.time() - start_time) > time_limit:
                break

            # Optional: After certain steps, shrink pool to speed up if many columns remain
            if steps_done >= 12 and len(remaining_idx) > 0:
                pool_size = max(8, pool_size // 2)

        # Append any remaining columns by initial ranking
        for idx in remaining_idx:
            selected_idx.append(idx)

        # Order column names accordingly
        ordered_cols = [col_names[i] for i in selected_idx]
        # Return re-ordered DataFrame
        return df_work[ordered_cols]
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple, Dict, Any


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
        df_prepared = self._apply_merges_as_strings(df, col_merge)
        if df_prepared.shape[1] <= 1:
            return df_prepared

        order = self._greedy_order(df_prepared)
        ordered_cols = [df_prepared.columns[i] for i in order]
        return df_prepared[ordered_cols]

    def _apply_merges_as_strings(self, df: pd.DataFrame, col_merge: Optional[List[List[Any]]]) -> pd.DataFrame:
        # Convert all to string once
        # Avoid deep copy; create new DataFrame with object dtype strings
        df_str = df.astype(str).copy()

        if not col_merge:
            return df_str

        # Normalize merge specs to column names
        cols_list = list(df_str.columns)
        name_set = set(cols_list)

        merged_cols_to_drop = set()
        merged_new_cols = []

        for idx, group in enumerate(col_merge):
            if not group:
                continue
            # Normalize group items to column names
            group_names = []
            for g in group:
                if isinstance(g, int):
                    if 0 <= g < len(cols_list):
                        cname = cols_list[g]
                        if cname in name_set:
                            group_names.append(cname)
                else:
                    if g in name_set:
                        group_names.append(g)
            # Ensure unique and preserve order in the given list
            if not group_names:
                continue
            # If only one column, treat as no-op, but still avoid duplicate merging
            if len(group_names) == 1:
                # nothing to merge; keep as is
                continue

            # Build merged column values row-wise
            # Use vectorized join via Python list comprehension over rows
            subvals = df_str[group_names].values.tolist()
            merged_vals = [''.join(row) for row in subvals]

            # Create new column name
            new_col_name = f"MERGED_{idx}"
            # Ensure uniqueness in case of clashes
            suffix = 1
            base_name = new_col_name
            while new_col_name in df_str.columns or new_col_name in merged_cols_to_drop:
                new_col_name = f"{base_name}_{suffix}"
                suffix += 1

            df_str[new_col_name] = merged_vals
            merged_new_cols.append(new_col_name)
            # Mark original group columns for removal
            for c in group_names:
                merged_cols_to_drop.add(c)

        if merged_cols_to_drop:
            # Drop merged columns
            remaining_cols = [c for c in df_str.columns if c not in merged_cols_to_drop]
            df_str = df_str[remaining_cols]

        return df_str

    def _factorize_column(self, arr: np.ndarray) -> Tuple[np.ndarray, Dict[Any, int]]:
        # Map each unique string value to an integer code in scan order
        n = arr.shape[0]
        codes = np.empty(n, dtype=np.int32)
        mapping: Dict[Any, int] = {}
        next_id = 0
        for i in range(n):
            v = arr[i]
            cid = mapping.get(v)
            if cid is None:
                cid = next_id
                mapping[v] = cid
                next_id += 1
            codes[i] = cid
        return codes, mapping

    def _compute_lengths(self, arr: np.ndarray) -> np.ndarray:
        # arr: numpy object array of strings
        # Compute lengths efficiently
        return np.fromiter((len(x) for x in arr), dtype=np.int32, count=arr.shape[0])

    def _evaluate_candidate_increment(self, prefix_ids: Optional[np.ndarray], cand_codes: np.ndarray, cand_lens: np.ndarray) -> int:
        n = cand_codes.shape[0]
        # Sum of lengths for rows where prefix+cand key has appeared before (in earlier indices)
        if prefix_ids is None:
            seen = set()
            total = 0
            for i in range(n):
                key = int(cand_codes[i])
                if key in seen:
                    total += int(cand_lens[i])
                else:
                    seen.add(key)
            return total
        else:
            seen = set()
            total = 0
            # Use tuple of (prefix_id, cand_code)
            for i in range(n):
                key = (int(prefix_ids[i]), int(cand_codes[i]))
                if key in seen:
                    total += int(cand_lens[i])
                else:
                    seen.add(key)
            return total

    def _build_new_prefix_ids(self, prefix_ids: Optional[np.ndarray], cand_codes: np.ndarray) -> np.ndarray:
        n = cand_codes.shape[0]
        if prefix_ids is None:
            # No need to remap: use candidate codes as prefix ids
            return cand_codes.copy()
        mapping: Dict[Tuple[int, int], int] = {}
        next_id = 0
        new_ids = np.empty(n, dtype=np.int32)
        for i in range(n):
            key = (int(prefix_ids[i]), int(cand_codes[i]))
            nid = mapping.get(key)
            if nid is None:
                nid = next_id
                mapping[key] = nid
                next_id += 1
            new_ids[i] = nid
        return new_ids

    def _greedy_order(self, df_str: pd.DataFrame) -> List[int]:
        cols = list(df_str.columns)
        m = len(cols)
        n = len(df_str)

        # Prepare arrays for each column
        # Convert columns to numpy object arrays
        col_arrays: List[np.ndarray] = [df_str[c].values.astype(object) for c in cols]
        col_lens: List[np.ndarray] = [self._compute_lengths(arr) for arr in col_arrays]
        col_codes: List[np.ndarray] = [self._factorize_column(arr)[0] for arr in col_arrays]

        remaining = set(range(m))
        order: List[int] = []
        prefix_ids: Optional[np.ndarray] = None

        # Tie-breaker heuristics precomputed
        # Distinct ratio and total length per column
        distinct_ratios: List[float] = []
        total_lens: List[int] = []
        for j in range(m):
            distinct_count = int(col_codes[j].max()) + 1 if col_codes[j].size > 0 else 0
            distinct_ratios.append(distinct_count / n if n > 0 else 0.0)
            total_lens.append(int(col_lens[j].sum()))

        while remaining:
            best_col = None
            best_score = -1

            # Evaluate each candidate
            for j in list(remaining):
                score = self._evaluate_candidate_increment(prefix_ids, col_codes[j], col_lens[j])
                if score > best_score:
                    best_score = score
                    best_col = j
                elif score == best_score and best_col is not None:
                    # Tie-breaker: prefer lower distinct ratio, then higher total length
                    dr_j = distinct_ratios[j]
                    dr_b = distinct_ratios[best_col]
                    if dr_j < dr_b or (dr_j == dr_b and total_lens[j] > total_lens[best_col]):
                        best_col = j

            # If all scores are zero (no duplicates), just pick by heuristic
            if best_score == 0:
                # Choose by ascending distinct ratio, then descending total length
                best_col = min(
                    remaining,
                    key=lambda j: (distinct_ratios[j], -total_lens[j]),
                )

            # Append chosen col and update prefix
            order.append(best_col)
            remaining.remove(best_col)
            prefix_ids = self._build_new_prefix_ids(prefix_ids, col_codes[best_col])

        return order
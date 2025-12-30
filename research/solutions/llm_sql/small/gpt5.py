import pandas as pd
import numpy as np
from typing import List, Dict, Tuple


def _lcp_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


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
        # Prepare merged columns as arrays of strings without creating heavy intermediate DataFrames
        n_rows = len(df)
        orig_cols = list(df.columns)

        # Build mapping from column to its merge group
        col_to_group: Dict[str, int] = {}
        groups: List[List[str]] = []
        if col_merge:
            for gi, grp in enumerate(col_merge):
                valid_grp = [c for c in grp if c in df.columns]
                if not valid_grp:
                    continue
                for c in valid_grp:
                    if c not in col_to_group:
                        col_to_group[c] = gi
                groups.append(valid_grp)
        # Build final column arrays and names after applying merges
        final_arrays: List[np.ndarray] = []
        final_names: List[str] = []
        processed_cols = set()

        # Helper to generate a unique merged name
        def merged_name(grp_cols: List[str], index: int) -> str:
            base = "MERGE_" + str(index) + "_" + "_".join(grp_cols)
            return base

        used_groups = set()
        for c in orig_cols:
            if c in processed_cols:
                continue
            if c in col_to_group:
                gid = col_to_group[c]
                if gid in used_groups:
                    continue
                # retrieve group columns preserving original order
                grp_cols = [col for col in orig_cols if col in col_to_group and col_to_group[col] == gid]
                if not grp_cols:
                    continue
                # build merged array
                arr = df[grp_cols[0]].astype(str).to_numpy(copy=False)
                # ensure np.str_ or python str; np.char.add handles both
                for col in grp_cols[1:]:
                    arr = np.char.add(arr, df[col].astype(str).to_numpy(copy=False))
                final_arrays.append(arr)
                final_names.append(merged_name(grp_cols, gid))
                for col in grp_cols:
                    processed_cols.add(col)
                used_groups.add(gid)
            else:
                arr = df[c].astype(str).to_numpy(copy=False)
                final_arrays.append(arr)
                final_names.append(c)
                processed_cols.add(c)

        # If no merges processed and no columns were added (unlikely), fallback to original as strings
        if not final_arrays:
            # convert all columns to string and return
            stringified = df.astype(str)
            return stringified

        K = len(final_arrays)
        N = n_rows

        # Precompute lengths per column, distinct ratio for tie-break, and sorted orders for scanning
        lens_list: List[np.ndarray] = []
        distinct_ratio: List[float] = []
        orders: List[np.ndarray] = []

        for arr in final_arrays:
            # length array
            lengths = np.fromiter((len(s) for s in arr), dtype=np.int32, count=N)
            lens_list.append(lengths)
            # distinct ratio
            try:
                # set() on numpy array of strings is OK
                uniq_count = len(set(arr.tolist()))
            except Exception:
                uniq_count = pd.Series(arr).nunique(dropna=False)
            distinct_ratio.append(uniq_count / N if N > 0 else 0.0)
            # sorted order
            # Using mergesort for stability, but default is fine
            try:
                order = np.argsort(arr, kind="mergesort")
            except Exception:
                # Fallback: Python sort by key
                order = np.array(sorted(range(N), key=lambda i: arr[i]), dtype=np.int64)
            orders.append(order)

        # Greedy construction of permutation
        selected: List[int] = []
        remaining: List[int] = list(range(K))

        # Initialize group ids (all rows in one group)
        grp_id = np.zeros(N, dtype=np.int64)

        # Initialize current best LCP length per row across selected prefix
        L = np.zeros(N, dtype=np.int32)

        # Prefix length (sum of lengths of selected columns) per row
        prefix_len = np.zeros(N, dtype=np.int32)

        # Pre-allocate best array to avoid reallocation overhead in loop
        best = np.empty(N, dtype=np.int32)

        while remaining:
            best_candidate = None
            best_gain = -1
            best_per_row_lcp: np.ndarray = None

            # Evaluate each remaining column as next choice
            for c in remaining:
                order = orders[c]
                vals = final_arrays[c]
                # Reset best to -1
                best.fill(-1)
                last_pos_by_group: Dict[int, int] = {}

                # Single left-to-right scan; for each pair of consecutive same-group elements,
                # compute LCP and update both rows' best LCP within this group for this column
                for pos in range(N):
                    idx_i = int(order[pos])
                    g = int(grp_id[idx_i])
                    prev_pos = last_pos_by_group.get(g)
                    if prev_pos is not None:
                        idx_j = int(order[prev_pos])
                        l = _lcp_len(vals[idx_i], vals[idx_j])
                        if l > best[idx_i]:
                            best[idx_i] = l
                        if l > best[idx_j]:
                            best[idx_j] = l
                    last_pos_by_group[g] = pos

                # Compute improvement: new LCP if this column appended now
                # candidate_subprefix = prefix_len + max(0, best)
                # improvement = max(0, candidate_subprefix - L)
                # Sum across rows
                np.maximum(best, 0, out=best)  # clip to [0, inf)
                candidate_subprefix = prefix_len + best
                delta = candidate_subprefix - L
                # Clip at zero
                delta[delta < 0] = 0
                gain = int(delta.sum())

                if gain > best_gain or (gain == best_gain and best_candidate is not None and distinct_ratio[c] < distinct_ratio[best_candidate]):
                    best_gain = gain
                    best_candidate = c
                    # Store a copy of best per row (since it'll be overwritten next iteration)
                    best_per_row_lcp = best.copy()

            # Append best_candidate to selection
            csel = best_candidate
            selected.append(csel)
            remaining.remove(csel)

            # Update L with contributions from new column using the best per-row lcp computed with old groups
            # Note: prefix_len still refers to previous prefix; use this then update prefix_len
            if best_per_row_lcp is not None:
                # clip best to >= 0
                best_imp = best_per_row_lcp
                candidate_subprefix = prefix_len + best_imp
                # L = max(L, candidate_subprefix)
                np.maximum(L, candidate_subprefix, out=L)

            # Update prefix_len to include full length of the selected column
            prefix_len = prefix_len + lens_list[csel]

            # Update group ids based on equality across selected prefix including the new column value
            # Next grouping: new_id = f(old_id, value_of_selected_column)
            new_grp_id = np.zeros(N, dtype=np.int64)
            map2id: Dict[Tuple[int, str], int] = {}
            next_id = 1
            vals_sel = final_arrays[csel]
            for i in range(N):
                key = (int(grp_id[i]), vals_sel[i])
                nid = map2id.get(key)
                if nid is None:
                    nid = next_id
                    next_id += 1
                    map2id[key] = nid
                new_grp_id[i] = nid
            grp_id = new_grp_id

        # Build output DataFrame with columns in selected order
        out = pd.DataFrame(index=df.index)
        for idx in selected:
            out[final_names[idx]] = final_arrays[idx]
        return out
import pandas as pd
import math
from typing import List, Dict, Tuple


def _lcp_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


class _ColumnInfo:
    __slots__ = (
        "name",
        "lens",
        "order",
        "rank",
        "lcp_arr",
        "st",
        "val_id",
        "unique_count",
        "sum_len",
        "values",
    )

    def __init__(self, name: str):
        self.name = name
        self.lens: List[int] = []
        self.order: List[int] = []
        self.rank: List[int] = []
        self.lcp_arr: List[int] = []
        self.st: List[List[int]] = []
        self.val_id: List[int] = []
        self.unique_count: int = 0
        self.sum_len: int = 0
        self.values: List[str] = []


def _build_sparse_table(arr: List[int]) -> List[List[int]]:
    n = len(arr)
    if n == 0:
        return []
    K = (n).bit_length()
    st = [arr[:]]
    k = 1
    while (1 << k) <= n:
        prev = st[k - 1]
        size = n - (1 << k) + 1
        curr = [0] * size
        half = 1 << (k - 1)
        for i in range(size):
            a = prev[i]
            b = prev[i + half]
            curr[i] = a if a < b else b
        st.append(curr)
        k += 1
    return st


def _rmq_query(st: List[List[int]], logs: List[int], l: int, r: int) -> int:
    # Query min on [l, r], assumes l <= r
    if l > r:
        return 0
    length = r - l + 1
    k = logs[length]
    a = st[k][l]
    b = st[k][r - (1 << k) + 1]
    return a if a < b else b


def _compute_column_info(df: pd.DataFrame, col: str, n_use: int, logs: List[int]) -> _ColumnInfo:
    ci = _ColumnInfo(col)
    # Extract string values for first n_use rows
    vals = df[col].astype(str).values[:n_use]
    # Convert to Python list of strings for faster access
    values = [str(v) for v in vals]
    ci.values = values
    n = len(values)
    lens = [len(v) for v in values]
    ci.lens = lens
    ci.sum_len = sum(lens)
    # Sorted order by values
    order = list(range(n))
    order.sort(key=values.__getitem__)
    ci.order = order
    rank = [0] * n
    for pos, idx in enumerate(order):
        rank[idx] = pos
    ci.rank = rank
    # Build lcp array between adjacent in sorted order
    if n >= 2:
        lcp_arr = [0] * (n - 1)
        prev_idx = order[0]
        prev_val = values[prev_idx]
        for i in range(n - 1):
            a_idx = order[i]
            b_idx = order[i + 1]
            lcp_arr[i] = _lcp_len(values[a_idx], values[b_idx])
        ci.lcp_arr = lcp_arr
        ci.st = _build_sparse_table(lcp_arr)
    else:
        ci.lcp_arr = []
        ci.st = []
    # Build value id per row based on equality groups in sorted order
    val_id = [0] * n
    unique_count = 0
    if n > 0:
        unique_count = 1
        val_id[order[0]] = 0
        last_val = values[order[0]]
        curr_id = 0
        for pos in range(1, n):
            idx = order[pos]
            v = values[idx]
            if v != last_val:
                curr_id += 1
                last_val = v
            val_id[idx] = curr_id
        unique_count = curr_id + 1
    ci.val_id = val_id
    ci.unique_count = unique_count
    return ci


def _subset_trie_cost(ci: _ColumnInfo, group_rows: List[int], logs: List[int]) -> int:
    # For the subset of rows, compute trie size for this column's values
    sz = len(group_rows)
    if sz == 0:
        return 0
    if sz == 1:
        return ci.lens[group_rows[0]]
    # Sum of lengths
    total_len = 0
    for r in group_rows:
        total_len += ci.lens[r]
    # Sort ranks
    ranks = [ci.rank[r] for r in group_rows]
    ranks.sort()
    # Sum of LCP between adjacent in sorted subset
    if not ci.st:
        # no lcp array (n_use<=1), but sz>=2 shouldn't happen; guard
        return total_len
    sum_lcp = 0
    for i in range(1, sz):
        r1 = ranks[i - 1]
        r2 = ranks[i]
        # lcp between ranks r1 and r2 is RMQ over lcp_arr indices [r1, r2-1]
        sum_lcp += _rmq_query(ci.st, logs, r1, r2 - 1)
    return total_len - sum_lcp


def _partition_by_column(ci: _ColumnInfo, group_rows: List[int]) -> List[List[int]]:
    buckets: Dict[int, List[int]] = {}
    get_val_id = ci.val_id.__getitem__
    for r in group_rows:
        vid = get_val_id(r)
        if vid in buckets:
            buckets[vid].append(r)
        else:
            buckets[vid] = [r]
    return list(buckets.values())


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
        # Apply column merges if specified
        df_mod = df.copy()
        if col_merge:
            used_cols = set()
            for idx, group in enumerate(col_merge):
                if not group:
                    continue
                cols = [c for c in group if c in df_mod.columns and c not in used_cols]
                if len(cols) <= 1:
                    for c in cols:
                        used_cols.add(c)
                    continue
                # Merge order as given in group list (filtered by existence)
                base_name = cols[0]
                # Build merged series
                s = df_mod[cols[0]].astype(str)
                for c in cols[1:]:
                    s = s + df_mod[c].astype(str)
                # Assign to base_name and drop others
                df_mod[base_name] = s
                for c in cols[1:]:
                    if c in df_mod.columns:
                        del df_mod[c]
                for c in cols:
                    used_cols.add(c)

        # Determine number of rows to use for optimization
        n_rows = len(df_mod)
        if n_rows == 0:
            return df_mod
        n_use = n_rows if early_stop is None else min(n_rows, int(early_stop))
        if n_use < 1:
            n_use = min(n_rows, 1)

        cols_list = list(df_mod.columns)
        m = len(cols_list)
        if m <= 1:
            return df_mod

        # Precompute log values for RMQ queries up to n_use
        max_len = max(1, n_use)
        logs = [0] * (max_len + 1)
        for i in range(2, max_len + 1):
            logs[i] = logs[i // 2] + 1

        # Build ColumnInfo for each column
        col_infos: List[_ColumnInfo] = []
        for c in cols_list:
            ci = _compute_column_info(df_mod, c, n_use, logs)
            col_infos.append(ci)

        # Greedy selection of columns minimizing incremental trie cost at each depth
        remaining = list(range(m))
        groups: List[List[int]] = [list(range(n_use))]
        order_idx: List[int] = []

        while remaining:
            best_col = None
            best_cost = None
            best_key = None
            for idx in remaining:
                ci = col_infos[idx]
                total_cost = 0
                for g in groups:
                    total_cost += _subset_trie_cost(ci, g, logs)
                # Tie-breaker: fewer unique values preferred; if still tie, larger total length; then name
                key = (ci.unique_count, -ci.sum_len, ci.name)
                if best_cost is None or total_cost < best_cost or (total_cost == best_cost and key < best_key):
                    best_cost = total_cost
                    best_col = idx
                    best_key = key
            order_idx.append(best_col)
            # Partition groups by the selected column's value IDs
            new_groups: List[List[int]] = []
            sel_ci = col_infos[best_col]
            for g in groups:
                parts = _partition_by_column(sel_ci, g)
                if parts:
                    if len(parts) == 1:
                        new_groups.append(parts[0])
                    else:
                        new_groups.extend(parts)
            groups = new_groups
            remaining.remove(best_col)

        ordered_cols = [cols_list[i] for i in order_idx]
        # Return DataFrame with reordered columns
        return df_mod[ordered_cols]

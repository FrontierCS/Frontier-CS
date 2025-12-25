import pandas as pd
import random
import math
from typing import List, Optional

class TrieNode:
    __slots__ = ('children',)
    def __init__(self):
        self.children = {}

def evaluate_order(order: List[str], col_strings: dict, sample_rows: int) -> int:
    """Return total LCP for the given column order on the sampled data."""
    root = TrieNode()
    total_lcp = 0
    for i in range(sample_rows):
        node = root
        lcp = 0
        for col in order:
            val = col_strings[col][i]
            if val in node.children:
                node = node.children[val]
                lcp += len(val)
            else:
                break
        total_lcp += lcp
        node = root
        for col in order:
            val = col_strings[col][i]
            if val not in node.children:
                node.children[val] = TrieNode()
            node = node.children[val]
    return total_lcp

def merge_columns(df: pd.DataFrame, col_merge: List[List[str]]) -> pd.DataFrame:
    """Merge columns according to col_merge specification."""
    if col_merge is None:
        return df.copy()
    df = df.copy()
    for group in col_merge:
        if not group:
            continue
        existing = [c for c in group if c in df.columns]
        if not existing:
            continue
        new_col = '_'.join(existing)
        df[new_col] = df[existing].apply(lambda row: ''.join(row.astype(str)), axis=1)
        df.drop(columns=existing, inplace=True)
    return df

def heuristic_order(df: pd.DataFrame, threshold: float) -> List[str]:
    """Propose an initial column order based on distinctness and average length."""
    columns = list(df.columns)
    if not columns:
        return []
    stats = []
    n = len(df)
    for col in columns:
        distinct = df[col].nunique()
        avg_len = df[col].astype(str).str.len().mean()
        distinct_ratio = distinct / n
        # score: higher for low distinct ratio and long strings
        score = (1 - distinct_ratio) * avg_len
        # optionally penalize columns above threshold
        if distinct_ratio > threshold:
            score *= 0.1
        stats.append((col, score))
    stats.sort(key=lambda x: x[1], reverse=True)
    return [col for col, _ in stats]

def simulated_annealing(
    df_sample: pd.DataFrame,
    initial_order: List[str],
    early_stop: int,
    col_stop: int,
    parallel: bool,
    threshold: float
) -> List[str]:
    """Improve column order using simulated annealing."""
    if len(initial_order) <= 1:
        return initial_order

    # Precompute string representations for the sample
    sample_rows = len(df_sample)
    col_strings = {col: df_sample[col].astype(str).tolist() for col in initial_order}

    current_order = initial_order[:]
    current_lcp = evaluate_order(current_order, col_strings, sample_rows)
    best_order = current_order[:]
    best_lcp = current_lcp

    T = 1.0
    T_min = 0.01
    cooling_rate = 0.995
    no_improve = 0
    max_no_improve = early_stop
    m = len(current_order)

    while T > T_min and no_improve < max_no_improve:
        # generate neighbor by swapping two columns within col_stop distance
        i = random.randrange(m)
        j = (i + random.randint(1, col_stop)) % m
        neighbor = current_order[:]
        neighbor[i], neighbor[j] = neighbor[j], neighbor[i]

        neighbor_lcp = evaluate_order(neighbor, col_strings, sample_rows)

        if neighbor_lcp > current_lcp or random.random() < math.exp((neighbor_lcp - current_lcp) / T):
            current_order = neighbor
            current_lcp = neighbor_lcp
            if neighbor_lcp > best_lcp:
                best_order = neighbor[:]
                best_lcp = neighbor_lcp
                no_improve = 0
            else:
                no_improve += 1
        else:
            no_improve += 1

        T *= cooling_rate

    return best_order

class Solution:
    def solve(
        self,
        df: pd.DataFrame,
        early_stop: int = 100000,
        row_stop: int = 4,
        col_stop: int = 2,
        col_merge: Optional[List[List[str]]] = None,
        one_way_dep: Optional[List] = None,
        distinct_value_threshold: float = 0.7,
        parallel: bool = True,
    ) -> pd.DataFrame:
        # Step 1: apply column merges
        df_merged = merge_columns(df, col_merge)

        if df_merged.empty:
            return df_merged

        # Step 2: determine sample for fast evaluation
        sample_size = min(row_stop, len(df_merged))
        if sample_size < len(df_merged):
            df_sample = df_merged.sample(n=sample_size, random_state=42).reset_index(drop=True)
        else:
            df_sample = df_merged.copy()

        # Step 3: compute initial heuristic order
        initial_order = heuristic_order(df_merged, distinct_value_threshold)

        # Step 4: improve order via simulated annealing (using sample)
        best_order = simulated_annealing(
            df_sample,
            initial_order,
            early_stop,
            col_stop,
            parallel,
            distinct_value_threshold
        )

        # Step 5: return DataFrame with optimized column order
        return df_merged[best_order]

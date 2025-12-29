import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple


def _mix64(a: int, b: int) -> int:
    # 64-bit mix function (xorshift + golden ratio + xor)
    a &= 0xFFFFFFFFFFFFFFFF
    b &= 0xFFFFFFFFFFFFFFFF
    x = a ^ (b + 0x9e3779b97f4a7c15 + ((a << 6) & 0xFFFFFFFFFFFFFFFF) + (a >> 2))
    return x & 0xFFFFFFFFFFFFFFFF


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
        df_proc = df
        if col_merge:
            df_proc = self._apply_merges(df_proc, col_merge)

        n_rows = len(df_proc)
        if n_rows == 0:
            return df_proc

        # Sample size for evaluation
        S = int(early_stop) if isinstance(early_stop, int) and early_stop > 0 else 100000
        S = min(n_rows, max(1, S))

        # Precompute per-column info over the sampled prefix of rows
        columns = list(df_proc.columns)
        col_info = self._prepare_columns_info(df_proc, columns, S)

        # Greedy ordering with incremental prefix-aware benefit evaluation
        order = self._greedy_order(columns, col_info, S, col_stop, distinct_value_threshold)

        # Return DataFrame with reordered columns
        return df_proc[order]

    def _apply_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        if not col_merge:
            return df

        df = df.copy()
        merge_count = 0
        for group in col_merge:
            # Validate group columns
            if not isinstance(group, (list, tuple)):
                continue
            valid_cols = [c for c in group if c in df.columns]
            if len(valid_cols) <= 1:
                # Nothing to merge if 0 or 1 column
                continue

            # Create merged column name
            new_col = f"_MERGE_{merge_count}"
            merge_count += 1

            # Concatenate string representations without separator
            # Using astype(str) handles numerics; fillna('') to avoid 'nan'
            merged_series = df[valid_cols].astype(str).fillna("").agg("".join, axis=1)

            # Drop original columns and add merged
            df = df.drop(columns=valid_cols)
            df[new_col] = merged_series

        return df

    def _prepare_columns_info(self, df: pd.DataFrame, columns: List[str], S: int) -> Dict[str, Dict[str, Any]]:
        col_info: Dict[str, Dict[str, Any]] = {}
        # Precompute for each column over first S rows:
        # - hashes: 64-bit integer hashes of string values
        # - lens: int lengths of string values
        # - score_first: benefit if the column is chosen first (duplicates across earlier rows)
        # - distinct_ratio: approximate distinct ratio (nunique/S) based on hashes
        for c in columns:
            # Extract sample and convert to string
            s = df[c].iloc[:S]
            # Convert to strings efficiently; fill None/NaN as empty string
            # astype(str) converts NaN to 'nan', so instead use map for NaN -> ''
            # To avoid overhead, use fillna('') then astype(str)
            s = s.fillna("").astype(str)
            vals = s.values  # numpy object array of Python strings

            # Compute hashes and lengths
            # Use Python's built-in hash for speed; mask to 64-bit to keep ints small
            hashes = np.empty(S, dtype=np.uint64)
            lens = np.empty(S, dtype=np.int32)

            # Vectorized-like via Python loop for speed and to avoid Python function call overhead per element
            for i in range(S):
                v = vals[i]
                lens[i] = len(v)
                hashes[i] = hash(v) & 0xFFFFFFFFFFFFFFFF

            # Compute distinct ratio
            # Using set of hashes as a proxy for unique counts (collision probability negligible)
            # To limit memory for very large S, but S <= 100k by default; acceptable
            uniq_count = len(set(hashes.tolist()))
            distinct_ratio = uniq_count / S if S > 0 else 1.0

            # Compute first-step benefit: sum of length for rows whose value seen earlier
            seen_vals = set()
            benefit = 0
            # Using local variables for speed
            hashes_local = hashes
            lens_local = lens
            for i in range(S):
                hv = int(hashes_local[i])
                if hv in seen_vals:
                    benefit += int(lens_local[i])
                else:
                    seen_vals.add(hv)

            col_info[c] = {
                "hashes": hashes,
                "lens": lens,
                "distinct_ratio": distinct_ratio,
                "score_first": benefit,
            }
        return col_info

    def _select_candidates(
        self,
        remaining: List[str],
        col_info: Dict[str, Dict[str, Any]],
        K: int,
        distinct_value_threshold: float,
    ) -> List[str]:
        if K >= len(remaining):
            # Evaluate all remaining
            return list(remaining)

        # Split columns into low-distinct and high-distinct groups based on threshold
        low = []
        high = []
        for c in remaining:
            if col_info[c]["distinct_ratio"] <= distinct_value_threshold:
                low.append(c)
            else:
                high.append(c)

        # Sort both groups by first-step benefit descending
        low_sorted = sorted(low, key=lambda x: col_info[x]["score_first"], reverse=True)
        high_sorted = sorted(high, key=lambda x: col_info[x]["score_first"], reverse=True)

        # Allocate K candidates: prioritize low-dist, but keep some diversity
        k_low = min(len(low_sorted), max(1, int(round(0.7 * K))))
        k_high = K - k_low
        if k_high > len(high_sorted):
            # Fill remainder from low if high is insufficient
            k_low = min(len(low_sorted), K)
            k_high = K - k_low

        candidates = low_sorted[:k_low] + high_sorted[:k_high]
        if len(candidates) < K:
            # Fill remaining slots from whichever group still has elements
            combined = low_sorted[k_low:] + high_sorted[k_high:]
            candidates += combined[: (K - len(candidates))]
        return candidates

    def _evaluate_incremental_benefit(
        self,
        prefix_hashes: np.ndarray,
        col_hashes: np.ndarray,
        col_lens: np.ndarray,
    ) -> int:
        # For the candidate column after current prefix:
        # Benefit = sum over rows of col_len[i] where (prefix_hash[i], col_hash[i]) was seen among earlier rows
        seen_pairs = set()
        benefit = 0
        S = len(prefix_hashes)
        # Localize
        pref = prefix_hashes
        h = col_hashes
        L = col_lens
        for i in range(S):
            pair_key = _mix64(int(pref[i]), int(h[i]))
            if pair_key in seen_pairs:
                benefit += int(L[i])
            else:
                seen_pairs.add(pair_key)
        return benefit

    def _update_prefix_hashes(
        self,
        prefix_hashes: np.ndarray,
        col_hashes: np.ndarray,
    ) -> None:
        S = len(prefix_hashes)
        pref = prefix_hashes
        h = col_hashes
        for i in range(S):
            pref[i] = _mix64(int(pref[i]), int(h[i]))

    def _greedy_order(
        self,
        columns: List[str],
        col_info: Dict[str, Dict[str, Any]],
        S: int,
        col_stop: int,
        distinct_value_threshold: float,
    ) -> List[str]:
        # Initialize prefix hashes to a constant seed for all sampled rows
        prefix_hashes = np.full(S, 0x9e3779b97f4a7c15 & 0xFFFFFFFFFFFFFFFF, dtype=np.uint64)

        remaining = list(columns)
        order: List[str] = []

        # Ensure at least 1 candidate per step
        K = max(1, int(col_stop)) if isinstance(col_stop, int) and col_stop > 0 else 2

        while remaining:
            # Select candidate columns to evaluate
            candidates = self._select_candidates(remaining, col_info, min(K, len(remaining)), distinct_value_threshold)

            # Evaluate incremental benefits for candidates
            best_col = None
            best_benefit = -1

            for c in candidates:
                benefit = self._evaluate_incremental_benefit(prefix_hashes, col_info[c]["hashes"], col_info[c]["lens"])
                if benefit > best_benefit:
                    best_benefit = benefit
                    best_col = c

            # Fallback to a deterministic choice if all benefits are equal (e.g., zero)
            if best_col is None:
                # Choose the column with highest first-step score among remaining
                best_col = max(remaining, key=lambda x: col_info[x]["score_first"])
                best_benefit = 0

            # Append to order and update prefix hashes
            order.append(best_col)
            self._update_prefix_hashes(prefix_hashes, col_info[best_col]["hashes"])
            remaining.remove(best_col)

        return order
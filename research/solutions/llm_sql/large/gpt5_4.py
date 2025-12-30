import pandas as pd
import numpy as np
from typing import List, Any, Dict


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
        # Step 1: Apply column merges if specified
        df2 = self._apply_col_merge(df, col_merge)

        # Step 2: Determine new column order using greedy heuristic
        order = self._find_best_order(
            df2,
            early_stop=early_stop,
            col_stop=col_stop,
            distinct_value_threshold=distinct_value_threshold,
        )

        # Step 3: Return DataFrame with reordered columns
        return df2[order]

    def _apply_col_merge(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        if not col_merge:
            return df.copy(deep=False)

        result = df.copy(deep=False)
        # We will work with a list of current columns to resolve integer indices
        def resolve_name_list(group: List[Any], current_cols: List[str]) -> List[str]:
            names = []
            for it in group:
                if isinstance(it, int):
                    idx = it if it >= 0 else len(current_cols) + it
                    if idx < 0 or idx >= len(current_cols):
                        continue
                    names.append(current_cols[idx])
                else:
                    name = str(it)
                    if name in current_cols:
                        names.append(name)
            # Deduplicate while preserving order
            seen = set()
            filtered = []
            for n in names:
                if n not in seen:
                    seen.add(n)
                    filtered.append(n)
            return filtered

        for group in col_merge:
            current_cols = list(result.columns)
            names = resolve_name_list(group, current_cols)
            if not names:
                continue
            if len(names) == 1:
                # Single column merge is effectively a rename; keep as-is
                base_name = names[0]
                new_name = f"{base_name}"
                # No need to change anything; continue
                continue
            # Build merged string column
            s = result[names[0]].astype(str).to_numpy()
            for nm in names[1:]:
                s = np.char.add(s, result[nm].astype(str).to_numpy())
            # Create a unique name for merged column
            merge_name_base = "MERGE_" + "||".join(names)
            new_name = merge_name_base
            k = 1
            existing = set(result.columns)
            while new_name in existing:
                new_name = f"{merge_name_base}#{k}"
                k += 1
            result[new_name] = s
            # Drop the original columns
            result.drop(columns=names, inplace=True)

        return result

    def _find_best_order(
        self,
        df: pd.DataFrame,
        early_stop: int,
        col_stop: int,
        distinct_value_threshold: float,
    ) -> List[str]:
        cols: List[str] = list(df.columns)
        n_rows = len(df)
        if n_rows == 0 or len(cols) <= 1:
            return cols

        # Sampling rows if dataset is very large (for speed); default early_stop=100000, so for typical sizes (~30k) we keep all
        if early_stop is not None and n_rows > early_stop:
            idx = np.arange(early_stop, dtype=np.int64)
        else:
            idx = None

        # Precompute factorized codes and string length statistics per column
        codes: Dict[str, np.ndarray] = {}
        avg_len: Dict[str, float] = {}
        uniq_counts: Dict[str, int] = {}
        static_score: Dict[str, float] = {}
        distinct_ratio: Dict[str, float] = {}

        # Helper to get series possibly sampled
        def get_series(col: str) -> pd.Series:
            s = df[col].astype(str)
            if idx is not None:
                return s.iloc[idx]
            return s

        for c in cols:
            s = get_series(c)
            lens = s.str.len().to_numpy(dtype=np.int32, copy=False)
            avg_len[c] = float(lens.mean()) if lens.size > 0 else 0.0
            lab, uniques = pd.factorize(s, sort=False)
            lab = lab.astype(np.int32, copy=False)
            codes[c] = lab
            ucount = int(uniques.size)
            uniq_counts[c] = ucount
            N = len(s)
            dr = ucount / N if N > 0 else 1.0
            distinct_ratio[c] = dr
            # Static score emphasizes duplication and length
            dup = max(0, N - ucount)
            base = dup * (avg_len[c] if avg_len[c] > 0 else 1.0)
            # Penalize high-distinct columns
            if dr > distinct_value_threshold:
                penalty_scale = max(0.05, 1.0 - (dr - distinct_value_threshold) / max(1e-9, 1.0 - distinct_value_threshold))
                base *= penalty_scale
            static_score[c] = base

        # Greedy selection using dynamic evaluation for early steps, then fallback to static
        remaining = cols.copy()
        selected: List[str] = []

        # Current group keys for selected prefix; start with zeros
        N_eff = len(codes[remaining[0]])  # length after potential sampling
        keys = np.zeros(N_eff, dtype=np.uint32)

        # Determine limits for dynamic evaluation
        # Candidate set size and number of dynamic steps scale with col_stop
        cand_limit = max(6, min(16, int(col_stop) * 8 if col_stop is not None else 12))
        dyn_steps = max(8, min(24, int(col_stop) * 8 if col_stop is not None else 16))
        dyn_steps = min(dyn_steps, len(remaining))

        # Sort remaining by static score initially
        remaining.sort(key=lambda x: static_score.get(x, 0.0), reverse=True)

        # Dynamic greedy phase
        for step in range(dyn_steps):
            if not remaining:
                break
            # Candidate pool: top by static score
            pool = remaining[: min(len(remaining), cand_limit)]
            best_col = None
            best_score = -1.0
            best_nuniq = None

            # If all candidates have near-unique values, we might break early to save time
            all_high_distinct = True

            for c in pool:
                if distinct_ratio[c] <= 0.98:
                    all_high_distinct = False
                    break

            # Evaluate dynamic scores for pool
            for c in pool:
                # Combine keys and codes for candidate column
                pair = (keys.astype(np.uint64) << np.uint64(32)) | codes[c].astype(np.uint64, copy=False)
                # Count unique pairs via factorize (hash-table based, O(N))
                _, uniq = pd.factorize(pair, sort=False)
                n_unique_pairs = int(uniq.size)
                # Score approximates expected added LCP length
                sc = (N_eff - n_unique_pairs) * (avg_len[c] if avg_len[c] > 0 else 1.0)
                # Small tie-breaking with static score
                sc += 1e-6 * static_score[c]
                if sc > best_score:
                    best_score = sc
                    best_col = c
                    best_nuniq = n_unique_pairs

            # If dynamic score yields no benefit or all candidates are high-distinct, switch to static order
            if best_col is None or best_score <= 0 or best_nuniq == N_eff or all_high_distinct:
                break

            # Select the best column and update keys
            selected.append(best_col)
            remaining.remove(best_col)
            pair = (keys.astype(np.uint64) << np.uint64(32)) | codes[best_col].astype(np.uint64, copy=False)
            new_keys, _ = pd.factorize(pair, sort=False)
            keys = new_keys.astype(np.uint32, copy=False)

            # Early stop if all rows are in unique groups already
            if len(np.unique(keys)) >= N_eff:
                break

        # Append remaining columns ordered by static score
        if remaining:
            remaining.sort(key=lambda x: static_score.get(x, 0.0), reverse=True)
            selected.extend(remaining)

        return selected
import numpy as np
import pandas as pd
from collections import defaultdict
from typing import List, Any, Dict, Tuple, Optional


class Solution:
    def _normalize_merge_group(self, group: Any, original_cols: List[Any]) -> List[Any]:
        if group is None:
            return []
        if isinstance(group, (str, int)):
            group = [group]
        out = []
        for x in group:
            if isinstance(x, (int, np.integer)):
                idx = int(x)
                if 0 <= idx < len(original_cols):
                    out.append(original_cols[idx])
            else:
                out.append(x)
        return out

    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        original_cols = list(df.columns)
        used = set()
        df2 = df

        for raw_group in col_merge:
            group = self._normalize_merge_group(raw_group, original_cols)
            if len(group) < 2:
                continue

            grp_cols = []
            for c in group:
                if c in df2.columns and c not in used:
                    grp_cols.append(c)
            if len(grp_cols) < 2:
                for c in grp_cols:
                    used.add(c)
                continue

            try:
                pos = min(df2.columns.get_loc(c) for c in grp_cols)
            except Exception:
                pos = 0

            s = df2[grp_cols].astype(str)
            merged = s[grp_cols[0]].str.cat([s[c] for c in grp_cols[1:]], sep="")

            new_name = grp_cols[0]
            if new_name in df2.columns and new_name not in grp_cols:
                base = str(new_name)
                k = 2
                while f"{base}__m{k}" in df2.columns:
                    k += 1
                new_name = f"{base}__m{k}"

            df2 = df2.drop(columns=grp_cols)
            df2.insert(pos, new_name, merged)

            for c in grp_cols:
                used.add(c)

        return df2

    def _collision_from_counts(self, counts: np.ndarray, n: int) -> float:
        if n <= 0:
            return 0.0
        ss = float(np.dot(counts, counts))
        return ss / float(n * n)

    def _prefix_collision(self, col_strings: np.ndarray, k: int) -> float:
        n = int(col_strings.shape[0])
        if n <= 0:
            return 0.0
        d = {}
        if k == 1:
            for s in col_strings:
                if s:
                    p = s[0]
                else:
                    p = ""
                d[p] = d.get(p, 0) + 1
        elif k == 2:
            for s in col_strings:
                if len(s) >= 2:
                    p = s[:2]
                elif s:
                    p = s
                else:
                    p = ""
                d[p] = d.get(p, 0) + 1
        else:
            for s in col_strings:
                p = s[:k] if s else ""
                d[p] = d.get(p, 0) + 1
        ss = 0
        for v in d.values():
            ss += v * v
        return float(ss) / float(n * n)

    def _mean_len(self, col_strings: np.ndarray) -> float:
        n = int(col_strings.shape[0])
        if n <= 0:
            return 0.0
        total = 0
        for s in col_strings:
            total += len(s)
        return float(total) / float(n)

    def _adjacent_equal_rate(self, col_strings: np.ndarray) -> float:
        n = int(col_strings.shape[0])
        if n <= 1:
            return 0.0
        eq = 0
        prev = col_strings[0]
        for i in range(1, n):
            cur = col_strings[i]
            if cur == prev:
                eq += 1
            prev = cur
        return float(eq) / float(n - 1)

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
        df2 = self._apply_col_merge(df, col_merge)
        cols = list(df2.columns)
        m = len(cols)
        n = len(df2)
        if m <= 1 or n <= 1:
            return df2

        max_sample = 6000
        if early_stop is not None:
            try:
                max_sample = min(max_sample, int(early_stop))
            except Exception:
                pass
        max_sample = max(500, max_sample)

        n_sample = min(n, max_sample)
        rng = np.random.default_rng(0)

        if n_sample < n:
            idx = rng.choice(n, size=n_sample, replace=False)
            sample_df = df2.iloc[idx]
        else:
            sample_df = df2

        n_adj = min(n, min(5000, max(500, n_sample)))
        adj_df = df2.iloc[:n_adj]

        sample_arr = sample_df.astype(str).to_numpy(dtype=object, copy=False)
        adj_arr = adj_df.astype(str).to_numpy(dtype=object, copy=False)

        metrics: Dict[Any, Dict[str, float]] = {}
        codes_map: Dict[Any, np.ndarray] = {}
        mult_map: Dict[Any, int] = {}

        n_s = int(sample_arr.shape[0])

        for j, c in enumerate(cols):
            col_strings = sample_arr[:, j]
            codes, uniques = pd.factorize(col_strings, sort=False)
            codes = codes.astype(np.int32, copy=False)
            codes_shift = (codes + 1).astype(np.int32, copy=False)

            nunique = int(len(uniques))
            distinct_ratio = float(nunique) / float(n_s) if n_s > 0 else 1.0

            counts = np.bincount(codes_shift, minlength=(nunique + 1))
            coll_full = self._collision_from_counts(counts, n_s)

            mean_len = self._mean_len(col_strings)
            coll_p1 = self._prefix_collision(col_strings, 1)
            coll_p2 = self._prefix_collision(col_strings, 2)

            adj_strings = adj_arr[:, j]
            adj_eq = self._adjacent_equal_rate(adj_strings)

            static_priority = (
                mean_len * (0.62 * coll_full + 0.23 * coll_p1 + 0.05 * coll_p2)
                + (mean_len * adj_eq) * 0.10
            )

            metrics[c] = {
                "distinct_ratio": distinct_ratio,
                "mean_len": mean_len,
                "coll_full": coll_full,
                "coll_p1": coll_p1,
                "coll_p2": coll_p2,
                "adj_eq": adj_eq,
                "priority": static_priority,
            }

            codes_map[c] = codes_shift
            mult_map[c] = int(codes_shift.max()) + 1

        base_sorted = sorted(
            cols,
            key=lambda c: (
                metrics[c]["distinct_ratio"],
                -metrics[c]["priority"],
                -metrics[c]["mean_len"],
            ),
        )

        max_greedy = 10 + max(0, int(col_stop)) * 6
        max_greedy = int(np.clip(max_greedy, 10, 24))
        max_greedy = min(max_greedy, m)

        cand_k = 22 + max(0, int(col_stop)) * 4
        cand_k = int(np.clip(cand_k, 18, 40))

        group = np.zeros(n_s, dtype=np.int32)
        groups_count = 1
        L = 0.0
        selected: List[Any] = []
        remaining = set(cols)

        # Put constant columns first (exactly one distinct in sample)
        constant_cols = [c for c in base_sorted if metrics[c]["distinct_ratio"] <= (1.0 / max(2, n_s))]
        for c in constant_cols:
            selected.append(c)
            remaining.remove(c)
            L += metrics[c]["mean_len"]
        # constants don't change grouping

        for _ in range(max_greedy - len(selected)):
            if not remaining:
                break
            matched_rows = n_s - groups_count
            if matched_rows < max(2, int(0.03 * n_s)):
                break

            rem_list = [c for c in base_sorted if c in remaining]
            if len(rem_list) > cand_k:
                candidates = rem_list[:cand_k]
            else:
                candidates = rem_list

            best_c = None
            best_score = None
            best_groups = None

            group_i64 = group.astype(np.int64, copy=False)
            for c in candidates:
                codes_c = codes_map[c].astype(np.int64, copy=False)
                mult = int(mult_map[c])

                pair = group_i64 * mult + codes_c
                groups_prime = int(np.unique(pair).size)

                score = float(n_s - groups_prime) * float(L + metrics[c]["mean_len"])

                if best_score is None or score > best_score:
                    best_score = score
                    best_c = c
                    best_groups = groups_prime

            if best_c is None:
                break

            codes_c = codes_map[best_c].astype(np.int64, copy=False)
            mult = int(mult_map[best_c])
            pair = group.astype(np.int64, copy=False) * mult + codes_c
            _, inv = np.unique(pair, return_inverse=True)
            group = inv.astype(np.int32, copy=False)
            groups_count = int(group.max()) + 1

            selected.append(best_c)
            remaining.remove(best_c)
            L += metrics[best_c]["mean_len"]

        remaining_list = [c for c in cols if c in remaining]
        remaining_sorted = sorted(
            remaining_list,
            key=lambda c: (
                metrics[c]["distinct_ratio"],
                -metrics[c]["priority"],
                -metrics[c]["mean_len"],
            ),
        )

        final_order = selected + remaining_sorted

        seen = set()
        final_order2 = []
        for c in final_order:
            if c in df2.columns and c not in seen:
                final_order2.append(c)
                seen.add(c)
        for c in df2.columns:
            if c not in seen:
                final_order2.append(c)
                seen.add(c)

        return df2.loc[:, final_order2]

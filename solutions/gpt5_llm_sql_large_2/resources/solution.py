import numpy as np
import pandas as pd
from typing import List, Optional, Any


class Solution:
    def _resolve_merge_group(self, df_cols: List[Any], group: Any) -> List[Any]:
        if group is None:
            return []
        resolved = []
        for g in group:
            if isinstance(g, (int, np.integer)):
                idx = int(g)
                if 0 <= idx < len(df_cols):
                    resolved.append(df_cols[idx])
            else:
                resolved.append(g)
        return resolved

    def _unique_col_name(self, existing: set, base: str) -> str:
        if base not in existing:
            return base
        k = 1
        while True:
            name = f"{base}_{k}"
            if name not in existing:
                return name
            k += 1

    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        df2 = df.copy(deep=False)
        existing = set(df2.columns)

        # Resolve int-based merges against original columns to avoid shifting index issues
        orig_cols = list(df2.columns)
        resolved_groups = []
        for grp in col_merge:
            cols = self._resolve_merge_group(orig_cols, grp)
            # De-dup while preserving order
            seen = set()
            cols = [c for c in cols if c not in seen and not seen.add(c)]
            resolved_groups.append(cols)

        for cols in resolved_groups:
            cols = [c for c in cols if c in df2.columns]
            if len(cols) < 2:
                continue

            locs = []
            for c in cols:
                try:
                    locs.append(int(df2.columns.get_loc(c)))
                except Exception:
                    pass
            if not locs:
                continue
            insert_pos = min(locs)

            base_name = "__".join(str(c) for c in cols)
            new_name = self._unique_col_name(existing - set(cols), base_name)
            existing.add(new_name)

            s = df2[cols[0]].astype(str)
            for c in cols[1:]:
                s = s + df2[c].astype(str)

            df2 = df2.drop(columns=cols)
            df2.insert(insert_pos, new_name, s)

        return df2

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
        if df is None or df.shape[1] <= 1 or df.shape[0] == 0:
            return df

        df2 = self._apply_col_merge(df, col_merge)
        cols = list(df2.columns)
        M = len(cols)
        N = len(df2)

        # Sampling
        base_sample = max(2000, int(row_stop) * 1000) if row_stop is not None else 4000
        cap_sample = 7000
        if early_stop is None or early_stop <= 0:
            early_stop = cap_sample
        n = int(min(N, max(1000, min(base_sample, cap_sample, early_stop))))
        if n < N:
            rng = np.random.default_rng(0)
            idx = rng.choice(N, size=n, replace=False)
            sample_df = df2.iloc[idx]
        else:
            sample_df = df2

        n = len(sample_df)
        if n <= 1 or M <= 1:
            return df2

        n2 = float(n) * float(n)

        codes_list = [None] * M
        bases = np.empty(M, dtype=np.uint32)
        avg_len = np.empty(M, dtype=np.float32)
        distinct_frac = np.empty(M, dtype=np.float32)
        collision = np.empty(M, dtype=np.float32)
        id_like = np.zeros(M, dtype=bool)

        for i, c in enumerate(cols):
            name = str(c).lower()
            if name == "id" or name.endswith("id") or name.endswith("_id") or "_id_" in name or "uuid" in name or "guid" in name:
                id_like[i] = True

            ser = sample_df[c]
            arr = ser.astype(str).to_numpy(dtype=object, copy=False)

            # Factorize
            codes, uniques = pd.factorize(arr, sort=False)
            if codes.dtype != np.int32 and codes.dtype != np.int64:
                codes = codes.astype(np.int32, copy=False)
            else:
                codes = codes.astype(np.int32, copy=False)
            if (codes < 0).any():
                # Shouldn't happen since we cast to str, but just in case
                codes = np.where(codes < 0, 0, codes).astype(np.int32, copy=False)

            k = int(len(uniques))
            if k <= 0:
                k = 1
            codes_u32 = codes.astype(np.uint32, copy=False)
            codes_list[i] = codes_u32
            bases[i] = np.uint32(k)

            counts = np.bincount(codes_u32, minlength=k).astype(np.int64, copy=False)
            cp = float(np.dot(counts, counts)) / n2
            collision[i] = cp
            distinct_frac[i] = float(k) / float(n)

            lengths = np.fromiter((len(x) for x in arr), dtype=np.int32, count=n)
            avg_len[i] = float(lengths.mean()) if n > 0 else 0.0

        # Greedy selection for a strong prefix
        K = int(min(M, max(10, min(16, M))))
        remaining = list(range(M))
        selected = []
        current_code = np.zeros(n, dtype=np.uint32)
        current_len = 0.0

        # Pre-sort remaining by simple usefulness to speed best-finding on many columns
        base_metric = (collision.astype(np.float64) * avg_len.astype(np.float64))
        pre_order = sorted(remaining, key=lambda j: (-base_metric[j], float(distinct_frac[j]), int(id_like[j]), str(cols[j])))
        remaining = pre_order

        for _ in range(K):
            if not remaining:
                break
            best_j = None
            best_val = -1.0
            best_raw = None

            for j in remaining:
                raw = current_code.astype(np.uint64) * np.uint64(bases[j]) + codes_list[j].astype(np.uint64)
                _, counts = np.unique(raw, return_counts=True)
                cp_new = float(np.dot(counts.astype(np.int64, copy=False), counts.astype(np.int64, copy=False))) / n2

                pen = 1.0
                if distinct_frac[j] >= distinct_value_threshold:
                    pen *= 0.2
                if id_like[j] and distinct_frac[j] >= 0.5:
                    pen *= 0.1

                val = (current_len + float(avg_len[j])) * cp_new * pen
                if val > best_val:
                    best_val = val
                    best_j = j
                    best_raw = raw

            if best_j is None:
                break

            _, inv = np.unique(best_raw, return_inverse=True)
            current_code = inv.astype(np.uint32, copy=False)
            current_len += float(avg_len[best_j])
            selected.append(best_j)
            remaining.remove(best_j)

            if current_len <= 0.0:
                continue
            # Early stop if additional columns are unlikely to help
            if len(selected) >= 8 and best_val < 0.1:
                break

        selected_set = set(selected)
        rest = [j for j in range(M) if j not in selected_set]

        def rest_key(j: int):
            high = distinct_frac[j] >= distinct_value_threshold
            il = bool(id_like[j])
            met = float(collision[j]) * float(avg_len[j])
            return (high, il, -met, str(cols[j]))

        rest_sorted = sorted(rest, key=rest_key)
        final_idx = selected + rest_sorted
        final_cols = [cols[i] for i in final_idx]

        return df2.loc[:, final_cols]

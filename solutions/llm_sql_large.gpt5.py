import pandas as pd
import numpy as np
from typing import List, Any, Dict, Tuple, Optional

class Solution:
    def __init__(self):
        self._rng = np.random.RandomState(0)

    @staticmethod
    def _normalize_col_ref(cols: List[Any], ref: Any) -> Any:
        if isinstance(ref, (int, np.integer)):
            if 0 <= int(ref) < len(cols):
                return cols[int(ref)]
            return None
        return ref

    @staticmethod
    def _unique_name(existing: set, base: str) -> str:
        if base not in existing:
            return base
        i = 1
        while True:
            cand = f"{base}__m{i}"
            if cand not in existing:
                return cand
            i += 1

    @staticmethod
    def _hash_series(s: pd.Series) -> np.ndarray:
        return pd.util.hash_pandas_object(s, index=False).to_numpy(dtype=np.uint64, copy=False)

    @staticmethod
    def _p_match(h: np.ndarray) -> float:
        n = h.size
        if n <= 1:
            return 1.0
        _, counts = np.unique(h, return_counts=True)
        counts = counts.astype(np.int64, copy=False)
        sumsq = int(np.dot(counts, counts))
        return float(sumsq) / float(n * n)

    @staticmethod
    def _mix64(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        # Both uint64 arrays
        return (a * np.uint64(11400714819323198485) +
                b * np.uint64(14029467366897019727) +
                np.uint64(0x9E3779B97F4A7C15))

    def _apply_merges(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        cols0 = list(df.columns)
        # Normalize groups to column names, filter invalid, and keep only existing
        groups: List[List[Any]] = []
        for g in col_merge:
            if not g or not isinstance(g, (list, tuple)):
                continue
            norm = []
            for ref in g:
                c = self._normalize_col_ref(cols0, ref)
                if c is None:
                    continue
                norm.append(c)
            # remove duplicates, keep order
            seen = set()
            norm2 = []
            for c in norm:
                if c in df.columns and c not in seen:
                    seen.add(c)
                    norm2.append(c)
            if len(norm2) >= 2:
                groups.append(norm2)

        if not groups:
            return df

        # Resolve overlaps: keep first occurrence
        assigned = {}
        final_groups = []
        for g in groups:
            g2 = [c for c in g if c not in assigned and c in df.columns]
            if len(g2) >= 2:
                for c in g2:
                    assigned[c] = len(final_groups)
                final_groups.append(g2)

        if not final_groups:
            return df

        group_first = {g[0]: idx for idx, g in enumerate(final_groups)}
        group_members = {idx: set(g) for idx, g in enumerate(final_groups)}

        existing = set(df.columns)
        merged_names = {}
        merged_series = {}

        for idx, g in enumerate(final_groups):
            base = "+".join(str(x) for x in g)
            name = self._unique_name(existing, base)
            existing.add(name)
            merged_names[idx] = name

            s = df[g[0]].astype(str)
            for c in g[1:]:
                s = s + df[c].astype(str)
            merged_series[idx] = s

        # Build new df with merged columns inserted at position of the first member
        new_cols = []
        for c in df.columns:
            if c in group_first:
                gid = group_first[c]
                new_cols.append(merged_names[gid])
            gid = assigned.get(c, None)
            if gid is not None and c in group_members[gid]:
                if c != final_groups[gid][0]:
                    continue
                else:
                    continue
            else:
                new_cols.append(c)

        # Remove duplicates in new_cols while preserving order
        seen = set()
        new_cols2 = []
        for c in new_cols:
            if c not in seen:
                seen.add(c)
                new_cols2.append(c)

        df2 = df.copy()
        for gid, name in merged_names.items():
            df2[name] = merged_series[gid]
        # Drop original merged members
        to_drop = []
        for g in final_groups:
            to_drop.extend(g)
        df2 = df2.drop(columns=[c for c in to_drop if c in df2.columns], errors="ignore")
        # Reindex columns to desired placement (some columns may have shifted; ensure all present)
        present = [c for c in new_cols2 if c in df2.columns]
        missing = [c for c in df2.columns if c not in set(present)]
        df2 = df2[present + missing]
        return df2

    @staticmethod
    def _enforce_one_way_deps(order: List[Any], one_way_dep: Optional[list]) -> List[Any]:
        if not one_way_dep:
            return order
        pos = {c: i for i, c in enumerate(order)}
        edges = []
        nodes = set(order)

        def norm_ref(ref):
            return ref

        for dep in one_way_dep:
            if not dep or not isinstance(dep, (list, tuple)) or len(dep) < 2:
                continue
            a = norm_ref(dep[0])
            b = norm_ref(dep[1])
            if a in nodes and b in nodes and a != b:
                edges.append((a, b))

        if not edges:
            return order

        indeg = {c: 0 for c in order}
        adj = {c: [] for c in order}
        for a, b in edges:
            adj[a].append(b)
            indeg[b] += 1

        # Kahn's algorithm with stable priority by original order
        import heapq
        heap = []
        for c in order:
            if indeg[c] == 0:
                heapq.heappush(heap, (pos[c], c))

        out = []
        while heap:
            _, u = heapq.heappop(heap)
            out.append(u)
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    heapq.heappush(heap, (pos[v], v))

        if len(out) != len(order):
            return order  # cycle or issue; keep original
        return out

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
        df2 = self._apply_merges(df, col_merge)
        cols = list(df2.columns)
        m = len(cols)
        n = len(df2)
        if m <= 1 or n <= 1:
            return df2

        prefix_k = int(row_stop) if row_stop is not None else 4
        if prefix_k < 1:
            prefix_k = 1
        if prefix_k > 8:
            prefix_k = 8

        greedy_steps = int(max(6, min(m, max(4, col_stop * 6 if col_stop is not None else 12))))
        greedy_steps = min(greedy_steps, m)

        pool_size = int(max(16, min(m, max(12, col_stop * 12 if col_stop is not None else 24))))
        pool_size = min(pool_size, m)

        sample_n = min(n, int(early_stop) if early_stop is not None else n, 8000)
        if sample_n < 1000:
            sample_n = min(n, 2000)
        if sample_n < 2:
            return df2

        if sample_n == n:
            idx = np.arange(n, dtype=np.int64)
        else:
            idx = self._rng.choice(n, size=sample_n, replace=False)
            idx.sort()

        # Precompute hashes and stats on sample
        col_hash: Dict[Any, np.ndarray] = {}
        p_equal: Dict[Any, float] = {}
        avg_len: Dict[Any, float] = {}
        e_col: Dict[Any, float] = {}
        distinct_ratio: Dict[Any, float] = {}

        n_s = sample_n
        denom = float(n_s * n_s)

        for c in cols:
            s = df2[c].iloc[idx].astype(str)
            lens = s.str.len().to_numpy(dtype=np.int32, copy=False)
            al = float(lens.mean()) if lens.size else 0.0
            avg_len[c] = al

            hf = self._hash_series(s)
            col_hash[c] = hf

            pe = self._p_match(hf)
            p_equal[c] = pe

            # distinct ratio (approx from hash uniques)
            uniq = int(np.unique(hf).size)
            dr = float(uniq) / float(n_s) if n_s else 1.0
            distinct_ratio[c] = dr

            # expected within-column LCP approximation (truncated at prefix_k + tail for exact)
            e_trunc = 0.0
            if prefix_k > 0:
                # To reduce overhead, compute prefixes only if column has some repetition or low distinctness,
                # else keep it minimal.
                # Still compute at least k=1 to capture common leading signs/digits.
                max_k = prefix_k
                if dr > 0.98 and prefix_k > 2:
                    max_k = 2
                for k in range(1, max_k + 1):
                    hp = self._hash_series(s.str.slice(0, k))
                    pk = self._p_match(hp)
                    e_trunc += pk

                if max_k < prefix_k:
                    # approximate remaining as pk at max_k
                    # (small weight; keeps deterministic)
                    e_trunc += 0.0

            tail = pe * max(al - float(prefix_k), 0.0)
            ec = e_trunc + tail
            if ec < 0.0:
                ec = 0.0
            e_col[c] = ec

        # Base scoring for candidate pool selection:
        # prioritize low distinctness and longer matches, but avoid putting very high distinct columns early.
        base = {}
        for c in cols:
            pe = p_equal[c]
            al = avg_len[c]
            ec = e_col[c]
            dr = distinct_ratio[c]
            # penalty for near-unique columns
            penalty = 1.0
            if dr >= distinct_value_threshold:
                penalty = max(0.1, 1.0 - (dr - distinct_value_threshold) / max(1e-9, (1.0 - distinct_value_threshold)))
            base[c] = penalty * (0.75 * (pe * al) + 0.25 * ec)

        ranked = sorted(cols, key=lambda c: base[c], reverse=True)
        pool = ranked[:pool_size]

        remaining_set = set(cols)
        chosen: List[Any] = []

        prefix_tuple_hash = np.zeros(n_s, dtype=np.uint64)
        p_prev = 1.0

        # Precompute for scaling
        mean_ec = float(np.mean([e_col[c] for c in cols])) if cols else 1.0
        if mean_ec <= 1e-9:
            mean_ec = 1.0

        for _ in range(greedy_steps):
            best_c = None
            best_score = None
            best_new_hash = None
            best_p_new = None

            # candidates: prefer pool first; if exhausted, fall back to remaining ranked
            cand_list = [c for c in pool if c in remaining_set]
            if not cand_list:
                cand_list = [c for c in ranked if c in remaining_set][:max(8, min(24, len(remaining_set)))]

            if not cand_list:
                break

            for c in cand_list:
                new_hash = self._mix64(prefix_tuple_hash, col_hash[c])
                p_new = self._p_match(new_hash)
                cond = p_new / p_prev if p_prev > 0.0 else 0.0

                # Objective: within-column expected LCP when we reach this column (scaled by p_prev),
                # plus continuation incentive for deeper columns (scaled by cond).
                score = (p_prev * e_col[c]) + (mean_ec * 1.2 * cond)

                if best_score is None or score > best_score:
                    best_score = score
                    best_c = c
                    best_new_hash = new_hash
                    best_p_new = p_new

            if best_c is None:
                break

            chosen.append(best_c)
            remaining_set.remove(best_c)
            prefix_tuple_hash = best_new_hash
            p_prev = float(best_p_new) if best_p_new is not None else p_prev

            # If exact matches are essentially gone, deeper columns are rarely reached; stop early.
            if p_prev <= (1.0 / float(n_s) + 1e-12):
                break

        remaining = [c for c in cols if c in remaining_set]
        # Sort remaining mainly by exact-match potential, with tie-breaker by within-column prefix potential
        remaining.sort(key=lambda c: (p_equal[c] * avg_len[c], e_col[c]), reverse=True)

        final_order = chosen + remaining
        final_order = self._enforce_one_way_deps(final_order, one_way_dep)

        # Ensure all columns included exactly once
        seen = set()
        final_order2 = []
        for c in final_order:
            if c in df2.columns and c not in seen:
                seen.add(c)
                final_order2.append(c)
        for c in df2.columns:
            if c not in seen:
                final_order2.append(c)
                seen.add(c)

        return df2[final_order2]

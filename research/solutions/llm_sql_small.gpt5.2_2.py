import time
from typing import List, Optional, Any, Dict, Tuple

import pandas as pd


class Solution:
    def _unique_column_name(self, existing: set, base: str) -> str:
        if base not in existing:
            return base
        k = 2
        while True:
            name = f"{base}__{k}"
            if name not in existing:
                return name
            k += 1

    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        df = df.copy()
        orig_cols = list(df.columns)
        existing = set(df.columns)

        for group in col_merge:
            if not group or len(group) < 2:
                continue

            names = []
            for g in group:
                if isinstance(g, int):
                    if 0 <= g < len(orig_cols):
                        names.append(orig_cols[g])
                else:
                    if g in df.columns:
                        names.append(g)

            if len(names) < 2:
                continue

            # de-duplicate in-order, and keep only columns still present
            seen = set()
            cleaned = []
            for nm in names:
                if nm in df.columns and nm not in seen:
                    cleaned.append(nm)
                    seen.add(nm)
            names = cleaned
            if len(names) < 2:
                continue

            base_name = "+".join(str(x) for x in names)
            new_name = self._unique_column_name(existing, base_name)
            existing.add(new_name)

            try:
                insert_at = min(df.columns.get_loc(nm) for nm in names)
            except Exception:
                insert_at = 0

            ser = df[names[0]].astype(str)
            for nm in names[1:]:
                ser = ser + df[nm].astype(str)

            df.insert(insert_at, new_name, ser)
            df.drop(columns=names, inplace=True, errors="ignore")

        return df

    def _trie_score(self, strings: List[str]) -> int:
        n = len(strings)
        if n <= 1:
            return 0

        nodes: List[Dict[str, int]] = [{}]
        total = 0

        for i, s in enumerate(strings):
            node = 0
            l = 0
            hit = True
            for ch in s:
                d = nodes[node]
                nxt = d.get(ch)
                if nxt is None:
                    nxt = len(nodes)
                    nodes.append({})
                    d[ch] = nxt
                    hit = False
                else:
                    if hit:
                        l += 1
                node = nxt
            if i:
                total += l

        return total

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
        t0 = time.perf_counter()
        time_limit = 8.8

        if df is None or df.shape[1] <= 1:
            return df

        df2 = self._apply_col_merge(df, col_merge)
        cols = list(df2.columns)
        m = len(cols)
        n_total = len(df2)

        if m <= 1:
            return df2

        if m > 12:
            # Fallback heuristic only
            dr = {}
            for c in cols:
                try:
                    dr[c] = float(df2[c].nunique(dropna=False)) / max(1, n_total)
                except Exception:
                    dr[c] = 1.0
            cols_sorted = sorted(
                cols,
                key=lambda c: (1 if dr[c] >= distinct_value_threshold else 0, dr[c]),
            )
            return df2[cols_sorted]

        sample_n = min(n_total, 3000)
        sample_df = df2.iloc[:sample_n]

        col_vals: List[List[str]] = []
        distinct_ratio: List[float] = []
        avg_len: List[float] = []
        prefix_strength: List[float] = []

        for c in cols:
            try:
                dr = float(df2[c].nunique(dropna=False)) / max(1, n_total)
            except Exception:
                dr = 1.0
            distinct_ratio.append(dr)

            s = sample_df[c].astype(str)
            v = s.tolist()
            col_vals.append(v)
            if v:
                al = sum(len(x) for x in v) / len(v)
            else:
                al = 0.0
            avg_len.append(al)

        # Column-only prefix strength (approx)
        for j in range(m):
            if time.perf_counter() - t0 > time_limit:
                prefix_strength = [0.0] * m
                break
            try:
                ps = float(self._trie_score(col_vals[j])) / max(1, sample_n - 1)
            except Exception:
                ps = 0.0
            prefix_strength.append(ps)

        def sort_key(idx: int):
            dr = distinct_ratio[idx]
            high = 1 if dr >= distinct_value_threshold else 0
            return (high, dr, -avg_len[idx], -prefix_strength[idx])

        def sort_remaining(rem: List[int]) -> List[int]:
            return sorted(rem, key=sort_key)

        score_cache: Dict[Tuple[int, ...], int] = {}

        def build_strings(order: List[int]) -> List[str]:
            if len(order) == 1:
                return col_vals[order[0]]
            vals = [col_vals[i] for i in order]
            return ["".join(parts) for parts in zip(*vals)]

        def score_order(order: List[int]) -> int:
            key = tuple(order)
            sc = score_cache.get(key)
            if sc is not None:
                return sc
            if time.perf_counter() - t0 > time_limit:
                sc = -1
                score_cache[key] = sc
                return sc
            strings = build_strings(order)
            sc = self._trie_score(strings)
            score_cache[key] = sc
            return sc

        all_idx = list(range(m))

        # Candidate initial orders
        candidates: List[List[int]] = []
        candidates.append(all_idx[:])
        candidates.append(sort_remaining(all_idx[:]))
        candidates.append(sorted(all_idx, key=lambda i: (distinct_ratio[i], -avg_len[i], -prefix_strength[i])))
        candidates.append(sorted(all_idx, key=lambda i: (-avg_len[i], distinct_ratio[i], -prefix_strength[i])))
        candidates.append(sorted(all_idx, key=lambda i: (-prefix_strength[i], distinct_ratio[i], -avg_len[i])))

        best_order = candidates[0]
        best_score = -1

        for cand in candidates:
            if time.perf_counter() - t0 > time_limit:
                break
            sc = score_order(cand)
            if sc > best_score:
                best_score = sc
                best_order = cand

        # Greedy with lookahead (complete remaining via heuristic)
        if time.perf_counter() - t0 <= time_limit:
            prefix: List[int] = []
            remaining = all_idx[:]
            best_overall_order = best_order[:]
            best_overall_score = best_score

            for _ in range(m):
                if time.perf_counter() - t0 > time_limit:
                    break
                best_c = None
                best_c_score = -10**18
                for c in remaining:
                    if time.perf_counter() - t0 > time_limit:
                        break
                    rem = [x for x in remaining if x != c]
                    order = prefix + [c] + sort_remaining(rem)
                    sc = score_order(order)
                    if sc > best_c_score:
                        best_c_score = sc
                        best_c = c
                if best_c is None:
                    break
                prefix.append(best_c)
                remaining.remove(best_c)

                order_now = prefix + sort_remaining(remaining)
                sc_now = score_order(order_now)
                if sc_now > best_overall_score:
                    best_overall_score = sc_now
                    best_overall_order = order_now

            if best_overall_score > best_score:
                best_score = best_overall_score
                best_order = best_overall_order

        # Local refinement: swaps and inserts
        def try_update(order: List[int], current_best_score: int, current_best_order: List[int]):
            sc = score_order(order)
            if sc > current_best_score:
                return sc, order
            return current_best_score, current_best_order

        if time.perf_counter() - t0 <= time_limit:
            improved = True
            passes = 0
            while improved and passes < 3 and (time.perf_counter() - t0) <= time_limit:
                improved = False
                passes += 1

                # Adjacent swaps first
                for i in range(m - 1):
                    if time.perf_counter() - t0 > time_limit:
                        break
                    cand = best_order[:]
                    cand[i], cand[i + 1] = cand[i + 1], cand[i]
                    new_score, new_order = try_update(cand, best_score, best_order)
                    if new_score > best_score:
                        best_score, best_order = new_score, new_order
                        improved = True

                # Any swaps
                for i in range(m - 1):
                    if time.perf_counter() - t0 > time_limit:
                        break
                    for j in range(i + 2, m):
                        if time.perf_counter() - t0 > time_limit:
                            break
                        cand = best_order[:]
                        cand[i], cand[j] = cand[j], cand[i]
                        new_score, new_order = try_update(cand, best_score, best_order)
                        if new_score > best_score:
                            best_score, best_order = new_score, new_order
                            improved = True

                # Insert moves
                for i in range(m):
                    if time.perf_counter() - t0 > time_limit:
                        break
                    for j in range(m):
                        if time.perf_counter() - t0 > time_limit:
                            break
                        if i == j:
                            continue
                        cand = best_order[:]
                        x = cand.pop(i)
                        cand.insert(j, x)
                        new_score, new_order = try_update(cand, best_score, best_order)
                        if new_score > best_score:
                            best_score, best_order = new_score, new_order
                            improved = True

        ordered_cols = [cols[i] for i in best_order]
        return df2[ordered_cols]
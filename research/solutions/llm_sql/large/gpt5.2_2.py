import numpy as np
import pandas as pd
from collections import defaultdict
import heapq


class Solution:
    def _safe_str_series(self, s: pd.Series) -> pd.Series:
        if s.isna().any():
            s = s.where(~s.isna(), "")
        return s.astype(str)

    def _resolve_merge_group(self, df: pd.DataFrame, group):
        cols = []
        for x in group:
            if isinstance(x, (int, np.integer)):
                if 0 <= int(x) < len(df.columns):
                    cols.append(df.columns[int(x)])
            else:
                if x in df.columns:
                    cols.append(x)
        seen = set()
        cols2 = []
        for c in cols:
            if c not in seen:
                cols2.append(c)
                seen.add(c)
        return cols2

    def _apply_merges(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        out = df
        modified = False

        for group in col_merge:
            cols = self._resolve_merge_group(out, group)
            if len(cols) < 2:
                continue
            if not all(c in out.columns for c in cols):
                continue

            base_name = "|".join(map(str, cols))
            name = base_name
            while name in out.columns and name not in cols:
                name = name + "_m"

            ser_list = [self._safe_str_series(out[c]) for c in cols]
            merged = ser_list[0].str.cat(ser_list[1:], sep="")
            if not modified:
                out = out.copy()
                modified = True
            out[name] = merged
            out.drop(columns=cols, inplace=True)

        return out

    def _topo_enforce(self, order, one_way_dep, df_columns):
        if not one_way_dep:
            return order

        pos = {c: i for i, c in enumerate(order)}
        edges = defaultdict(list)
        indeg = defaultdict(int)

        def _to_name(x):
            if isinstance(x, (int, np.integer)):
                xi = int(x)
                if 0 <= xi < len(df_columns):
                    return df_columns[xi]
                return None
            return x

        for dep in one_way_dep:
            if not dep or len(dep) < 2:
                continue
            a = _to_name(dep[0])
            b = _to_name(dep[1])
            if a is None or b is None:
                continue
            if a not in pos or b not in pos:
                continue
            if a == b:
                continue
            edges[a].append(b)
            indeg[b] += 1
            indeg.setdefault(a, indeg.get(a, 0))

        if not edges:
            return order

        heap = []
        for c in order:
            if indeg.get(c, 0) == 0:
                heapq.heappush(heap, (pos[c], c))

        res = []
        indeg_local = dict(indeg)
        while heap:
            _, u = heapq.heappop(heap)
            if u in res:
                continue
            res.append(u)
            for v in edges.get(u, []):
                indeg_local[v] -= 1
                if indeg_local[v] == 0:
                    heapq.heappush(heap, (pos[v], v))

        if len(res) != len(order):
            return order
        return res

    def _compute_stats(self, df: pd.DataFrame, cols, n_s: int):
        stats = {}
        mask32 = np.uint64(0xFFFFFFFF)

        for c in cols:
            arr = df[c].iloc[:n_s].to_numpy(copy=False)
            m = pd.isna(arr)
            s = arr.astype(str, copy=False)
            if m.any():
                s = np.array(s, copy=True)
                s[m] = ""
            codes, uniques = pd.factorize(s, sort=False)
            n_uni = len(uniques)
            if n_uni == 0:
                codes_u32 = np.zeros(n_s, dtype=np.uint32)
                len_unique = np.zeros(1, dtype=np.int32)
                counts = np.zeros(1, dtype=np.int32)
                distinct_ratio = 1.0
                avg_len = 0.0
                dup_len = 0.0
                top_freq = 1.0
                skew1 = 1.0
                skew2 = 1.0
            else:
                codes_u32 = codes.astype(np.uint32, copy=False)
                counts = np.bincount(codes, minlength=n_uni).astype(np.int32, copy=False)
                uniq_arr = np.asarray(uniques, dtype=str)

                len_unique = np.fromiter((len(x) for x in uniq_arr), dtype=np.int32, count=n_uni)
                sum_count_len = int(np.dot(counts.astype(np.int64), len_unique.astype(np.int64)))
                avg_len = sum_count_len / float(n_s)
                dup_len = float(sum_count_len - int(len_unique.sum()))

                distinct_ratio = n_uni / float(n_s)
                top_freq = float(counts.max()) / float(n_s) if n_s > 0 else 0.0

                d1 = {}
                d2 = {}
                for u, cnt in zip(uniq_arr, counts):
                    p1 = u[:1]
                    p2 = u[:2]
                    d1[p1] = d1.get(p1, 0) + int(cnt)
                    d2[p2] = d2.get(p2, 0) + int(cnt)
                skew1 = (max(d1.values()) / float(n_s)) if d1 else 0.0
                skew2 = (max(d2.values()) / float(n_s)) if d2 else 0.0

            prefix_score = 0.5 * skew1 + 0.3 * skew2 + 0.2 * top_freq
            effective = distinct_ratio / (0.05 + prefix_score)

            stats[c] = {
                "codes": codes_u32,
                "len_unique": len_unique,
                "distinct_ratio": distinct_ratio,
                "avg_len": float(avg_len),
                "dup_len": float(dup_len),
                "prefix_score": float(prefix_score),
                "effective": float(effective),
                "mask32": mask32,
            }

        return stats

    def _conditional_dup_score(self, group_ids_u64, col_codes_u32, len_unique):
        pair = (group_ids_u64 << 32) | col_codes_u32.astype(np.uint64, copy=False)
        uniq_pairs, counts = np.unique(pair, return_counts=True)
        m = counts > 1
        if not np.any(m):
            return 0.0
        counts2 = counts[m].astype(np.int64, copy=False) - 1
        val_codes = (uniq_pairs[m] & np.uint64(0xFFFFFFFF)).astype(np.int64, copy=False)
        lens = len_unique[val_codes].astype(np.int64, copy=False)
        return float(np.dot(counts2, lens))

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
        if df is None or df.shape[1] <= 1:
            return df

        df2 = self._apply_merges(df, col_merge)

        cols = list(df2.columns)
        m = len(cols)
        if m <= 1:
            return df2

        n = len(df2)
        if n <= 1:
            return df2

        try:
            es = int(early_stop) if early_stop is not None else n
        except Exception:
            es = n
        n_s = min(n, max(1, es))

        stats = self._compute_stats(df2, cols, n_s)

        try:
            greedy_k = int(col_stop) if col_stop is not None else 0
        except Exception:
            greedy_k = 0
        greedy_k = max(0, min(greedy_k, m))

        remaining = cols[:]
        greedy_cols = []
        group_ids = None

        for _ in range(greedy_k):
            if not remaining:
                break

            best_c = None
            best_score = -1.0

            if group_ids is None:
                for c in remaining:
                    info = stats[c]
                    score = info["dup_len"] + 0.05 * info["prefix_score"] * info["avg_len"] * float(n_s)
                    if score > best_score:
                        best_score = score
                        best_c = c
            else:
                for c in remaining:
                    info = stats[c]
                    score = self._conditional_dup_score(group_ids, info["codes"], info["len_unique"])
                    score += 0.01 * info["prefix_score"] * info["avg_len"] * float(n_s)
                    if score > best_score:
                        best_score = score
                        best_c = c

            if best_c is None:
                break

            greedy_cols.append(best_c)
            remaining.remove(best_c)

            if group_ids is None:
                group_ids = stats[best_c]["codes"].astype(np.uint64, copy=False)
            else:
                pair = (group_ids << 32) | stats[best_c]["codes"].astype(np.uint64, copy=False)
                group_ids = pd.factorize(pair, sort=False)[0].astype(np.uint64, copy=False)

        low = []
        high = []
        for c in remaining:
            if stats[c]["distinct_ratio"] <= distinct_value_threshold:
                low.append(c)
            else:
                high.append(c)

        low.sort(
            key=lambda c: (
                stats[c]["effective"],
                stats[c]["distinct_ratio"],
                -stats[c]["dup_len"],
                -stats[c]["prefix_score"],
                -stats[c]["avg_len"],
            )
        )
        high.sort(
            key=lambda c: (
                stats[c]["distinct_ratio"],
                -stats[c]["prefix_score"],
                -stats[c]["avg_len"],
                -stats[c]["dup_len"],
            )
        )

        order = greedy_cols + low + high
        order = self._topo_enforce(order, one_way_dep, list(df2.columns))

        return df2[order]
import pandas as pd
import numpy as np
from typing import List, Any, Dict, Tuple, Optional


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        df = df.copy()
        for gi, group in enumerate(col_merge):
            if not group:
                continue

            cols = []
            for x in group:
                if isinstance(x, int):
                    if 0 <= x < len(df.columns):
                        cols.append(df.columns[x])
                else:
                    if x in df.columns:
                        cols.append(x)

            seen = set()
            cols = [c for c in cols if (c not in seen and not seen.add(c))]
            if len(cols) <= 1:
                continue

            positions = [df.columns.get_loc(c) for c in cols if c in df.columns]
            if not positions:
                continue
            insert_pos = int(min(positions))

            merged = df[cols[0]].astype(str)
            for c in cols[1:]:
                merged = merged + df[c].astype(str)

            base_name = "MERGE_" + str(gi)
            name = base_name
            k = 1
            while name in df.columns:
                name = f"{base_name}_{k}"
                k += 1

            df.drop(columns=cols, inplace=True)
            df.insert(insert_pos, name, merged)

        return df

    @staticmethod
    def _group_contrib(keys: np.ndarray, plen: np.ndarray) -> np.int64:
        n = keys.size
        if n <= 1:
            return np.int64(0)
        order = np.argsort(keys, kind="quicksort")
        sk = keys[order]
        sp = plen[order]
        diff = sk[1:] != sk[:-1]
        if not diff.any():
            # one group
            return np.int64((n - 1) * int(sp[0]))
        starts = np.empty(diff.sum() + 1, dtype=np.int32)
        starts[0] = 0
        starts[1:] = np.nonzero(diff)[0].astype(np.int32) + 1
        ends = np.empty(starts.size, dtype=np.int32)
        ends[:-1] = starts[1:]
        ends[-1] = n
        counts = (ends - starts).astype(np.int64)
        contrib = ((counts - 1) * sp[starts].astype(np.int64)).sum(dtype=np.int64)
        return contrib

    def _optimize_order(
        self,
        df: pd.DataFrame,
        distinct_value_threshold: float = 0.7,
        early_stop: int = 100000,
        row_stop: int = 4,
        col_stop: int = 2,
    ) -> List[Any]:
        cols = list(df.columns)
        m = len(cols)
        if m <= 1:
            return cols

        n = len(df)
        if n <= 1:
            return cols

        sample_max = 6000
        sample_min = 2000
        sample_n = min(n, sample_max)
        if sample_n < sample_min:
            sample_n = min(n, sample_min)

        if sample_n < n:
            rng = np.random.default_rng(0)
            idx = rng.choice(n, size=sample_n, replace=False)
            sample = df.iloc[idx]
        else:
            sample = df

        n_sample = len(sample)
        n2 = float(n_sample) * float(n_sample)

        codes_list: List[np.ndarray] = []
        lens_list: List[np.ndarray] = []
        distinct_ratio = np.empty(m, dtype=np.float64)
        avg_len = np.empty(m, dtype=np.float64)
        simpson_exact = np.empty(m, dtype=np.float64)
        score_ind = np.empty(m, dtype=np.float64)

        for i, c in enumerate(cols):
            s = sample[c].astype(str)
            l = s.str.len().to_numpy(np.int32, copy=False)
            avg_l = float(l.mean()) if n_sample else 0.0

            codes, uniques = pd.factorize(s, sort=False)
            if codes.dtype != np.int32 and codes.dtype != np.int64:
                codes = codes.astype(np.int32, copy=False)
            if codes.min(initial=0) < 0:
                codes = codes.astype(np.int64, copy=False)
                codes[codes < 0] = 0
                codes = codes.astype(np.int32, copy=False)

            u = int(len(uniques))
            if u <= 0:
                u = 1

            cnt = np.bincount(codes, minlength=u).astype(np.int64, copy=False)
            sx = float(np.dot(cnt, cnt)) / n2

            distinct_ratio[i] = float(u) / float(n_sample) if n_sample else 1.0
            avg_len[i] = avg_l
            simpson_exact[i] = sx

            # Approx expected LCP within this column up to kmax chars, plus exact-match tail.
            kmax = 3
            pk_sum = 0.0
            for k in (1, 2, 3):
                mask = l >= k
                if not bool(mask.any()):
                    break
                sub = s[mask]
                pref = sub.str.slice(0, k)
                pcodes, pun = pd.factorize(pref, sort=False)
                u2 = int(len(pun))
                if u2 <= 0:
                    u2 = 1
                pcnt = np.bincount(pcodes, minlength=u2).astype(np.int64, copy=False)
                pk_sum += float(np.dot(pcnt, pcnt)) / n2

            tail = max(0.0, avg_l - float(kmax)) * sx
            score_ind[i] = pk_sum + tail

            codes_list.append(codes.astype(np.uint32, copy=False))
            lens_list.append(l)

        # Greedy choose first K columns using exact-match grouping on sample
        K = min(10, m)
        P = np.uint64(1315423911)
        keys_base = np.zeros(n_sample, dtype=np.uint64)
        plen_base = np.zeros(n_sample, dtype=np.int32)

        remaining = list(range(m))
        selected: List[int] = []

        cand_thresh = max(0.85, float(distinct_value_threshold))

        for step in range(K):
            if not remaining:
                break

            if step <= 1:
                cand = remaining
            else:
                cand = [j for j in remaining if distinct_ratio[j] <= cand_thresh]
                if not cand:
                    cand = remaining

            best_j = None
            best_score = None

            for j in cand:
                keys_new = keys_base * P + codes_list[j].astype(np.uint64) + np.uint64(1)
                plen_new = plen_base + lens_list[j]
                sc = self._group_contrib(keys_new, plen_new)

                if best_score is None or sc > best_score:
                    best_score = sc
                    best_j = j
                elif sc == best_score:
                    if score_ind[j] > score_ind[best_j]:
                        best_j = j

            if best_j is None:
                break

            selected.append(best_j)
            keys_base = keys_base * P + codes_list[best_j].astype(np.uint64) + np.uint64(1)
            plen_base = plen_base + lens_list[best_j]
            remaining.remove(best_j)

            # Early stop if keys almost all unique and little further gain expected
            if step >= 2 and distinct_ratio[best_j] > 0.98:
                break

        # Order the rest by independent score; push very distinct columns later
        if remaining:
            rem = np.array(remaining, dtype=np.int32)
            # sort key: (is_high_distinct, -score_ind, distinct_ratio, -avg_len)
            high = (distinct_ratio[rem] > distinct_value_threshold).astype(np.int32)
            order = np.lexsort((
                -avg_len[rem],
                distinct_ratio[rem],
                -score_ind[rem],
                high,
            ))
            remaining_sorted = rem[order].tolist()
        else:
            remaining_sorted = []

        final_idx = selected + remaining_sorted
        return [cols[i] for i in final_idx]

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
        if df2.shape[1] <= 1:
            return df2

        order = self._optimize_order(
            df2,
            distinct_value_threshold=distinct_value_threshold,
            early_stop=early_stop,
            row_stop=row_stop,
            col_stop=col_stop,
        )
        try:
            return df2[order]
        except Exception:
            # Fallback to original if something unexpected happens
            return df2.copy()
